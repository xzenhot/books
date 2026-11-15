using System;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;

using WriterWorker.Configuration;
using WriterWorker.Ctl;
using WriterWorker.Models;

namespace WriterWorker.Views;

/// <summary>
/// Designs one page of a book - the blurb, the title, the publisher page, the dedication, the
/// copyright page, the foreword or the appendix - in a rich text editor laid out on a sheet the size
/// of the printed page, and writes the result to the RTF file the <c>paths</c> of its page folder
/// records. A page that has no file yet is started from the details of the book and added to the
/// pages of its part, so it prints as soon as it is saved.
/// </summary>
public partial class PageDesignerWindow : Window
{
    private const double MillimetresPerInch = 25.4;
    private const double PixelsPerInch = 96;

    private readonly string _bookFolder;
    private readonly PageGroupRole _role;
    private readonly string _name;
    private readonly BookMetadata? _book;

    private bool _loading;
    private bool _dirty;

    /// <param name="bookFolder">Folder of the book the page belongs to.</param>
    /// <param name="role">Part of the book the page belongs to.</param>
    /// <param name="name">Name of the page, for example <c>title</c>.</param>
    /// <param name="layout">Page setup the sheet is laid out with; the book page size when null.</param>
    /// <param name="book">Details the starter text is built from.</param>
    public PageDesignerWindow(
        string bookFolder,
        PageGroupRole role,
        string name,
        PdfExportOptions? layout = null,
        BookMetadata? book = null)
    {
        InitializeComponent();

        _bookFolder = Path.GetFullPath(bookFolder);
        _role = role;
        _name = BookPages.NameOfFile(name);
        _book = book;

        Title = $"Design {BookPages.DisplayNameOfFile(_name)}";
        PageTitleText.Text = BookPages.DisplayNameOfFile(_name);

        FilePath = PathOf(_role, _name);
        PagePathText.Text = BookPages.Relative(ProfileBase, FilePath);

        SizeSheet(layout);
        LoadPage();

        Editor.TextChanged += OnEditorTextChanged;
        PreviewKeyDown += OnPreviewKeyDown;
        Loaded += (_, _) => Editor.Focus();
    }

    /// <summary>Folder the page paths of the profile of the book are recorded against.</summary>
    private string ProfileBase => BookProfile.ProfileFolderOf(_bookFolder);

    /// <summary>RTF file the page is read from and written to.</summary>
    public string FilePath { get; }

    /// <summary>Whether the page was written to disk from this window.</summary>
    public bool Saved { get; private set; }

    /// <summary>Whether the design differs from the file on disk.</summary>
    public bool IsDirty => _dirty;

    protected override void OnClosing(CancelEventArgs e)
    {
        if (_dirty)
        {
            var answer = MessageBox.Show(
                this,
                $"Save the changes to the {BookPages.DisplayNameOfFile(_name).ToLowerInvariant()}?",
                "Design page",
                MessageBoxButton.YesNoCancel,
                MessageBoxImage.Question);

            if (answer == MessageBoxResult.Cancel)
            {
                e.Cancel = true;
                return;
            }

            if (answer == MessageBoxResult.Yes)
            {
                SavePage(close: false);
            }
        }

        base.OnClosing(e);
    }

    /// <summary>
    /// Lays the sheet out at the size of the printed page and pads the editor by the margin of the
    /// page, so the design is seen inside the area the printer can reach.
    /// </summary>
    private void SizeSheet(PdfExportOptions? layout)
    {
        var widthMm = layout is { PageWidthMm: > 0 } ? layout.PageWidthMm : 148;
        var heightMm = layout is { PageHeightMm: > 0 } ? layout.PageHeightMm : 210;
        var marginMm = layout is { MarginMm: >= 0 } ? layout.MarginMm : 20;

        PageSheet.Width = Math.Round(widthMm / MillimetresPerInch * PixelsPerInch);
        PageSheet.Height = Math.Round(heightMm / MillimetresPerInch * PixelsPerInch);

        // The margin is drawn inside the sheet, but never so wide that the page has no room left.
        var margin = Math.Min(marginMm, Math.Min(widthMm, heightMm) / 3) / MillimetresPerInch * PixelsPerInch;
        Editor.Padding = new Thickness(margin);

        if (layout?.FontFamily is { Length: > 0 } family)
        {
            Editor.FontFamily = new FontFamily(family);
        }
        else
        {
            Editor.FontFamily = new FontFamily("Georgia");
        }

        if (layout?.FontSize is { } points)
        {
            Editor.FontSize = points;
        }

        StatusText.Text = string.Format(
            CultureInfo.CurrentCulture,
            "{0} x {1} mm page with a {2} mm margin, saved as RTF.",
            widthMm.ToString("0.##", CultureInfo.CurrentCulture),
            heightMm.ToString("0.##", CultureInfo.CurrentCulture),
            marginMm.ToString("0.##", CultureInfo.CurrentCulture));

        Width = Math.Clamp(PageSheet.Width + 180, 560, 1200);
        Height = Math.Clamp(PageSheet.Height + 300, 520, 1000);
    }

    /// <summary>
    /// Absolute path of the design of <paramref name="name"/>: the file its page folder records when
    /// that is on disk, the recorded file when it is still to be made, and otherwise the file named
    /// after the page in the folder of its part of the book. A page folder or a design still named
    /// with the order prefix of an older version is renamed first, so the file the page is saved to is
    /// named after the page it designs.
    /// </summary>
    private string PathOf(PageGroupRole role, string name)
    {
        PageStore.StripFolderPrefixes(_bookFolder);
        PageStore.StripOrderPrefixes(_bookFolder);

        var group = PageStore.GroupOf(_bookFolder, role);

        if (group?.Files.FirstOrDefault(file => string.Equals(file.Name, name, StringComparison.OrdinalIgnoreCase)) is { } listed
            && BookPages.Resolve(ProfileBase, listed.FilePath) is { } recorded
            && (File.Exists(recorded) || !PageStore.IsLegacy(listed.FilePath)))
        {
            return recorded;
        }

        var folder = group?.FilePath ?? BookPages.FolderPathOf(role);

        return BookPages.Resolve(ProfileBase, folder + name + BookPages.RtfExtension)
            ?? Path.Combine(PageStore.FolderIn(_bookFolder), name + BookPages.RtfExtension);
    }

    /// <summary>Reads the page from its file, or starts it from the text built from the book.</summary>
    private void LoadPage()
    {
        _loading = true;
        try
        {
            if (File.Exists(FilePath))
            {
                RtfExport.Load(Editor, FilePath);
            }
            else
            {
                Editor.Document = PageStore.CreateStarterDocument(_bookFolder, _name, _book);
            }

            Editor.Document.PagePadding = new Thickness(0);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException
            or ArgumentException)
        {
            StatusText.Text = $"The page could not be read: {exception.Message}";
        }
        finally
        {
            _loading = false;
        }

        _dirty = false;
    }

    private void OnEditorTextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
    {
        if (_loading)
        {
            return;
        }

        _dirty = true;
        SaveButton.IsEnabled = true;
    }

    private void OnPreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.S && Keyboard.Modifiers == ModifierKeys.Control)
        {
            SavePage(close: false);
            e.Handled = true;
        }
    }

    private void Save_Click(object sender, RoutedEventArgs e) => SavePage(close: true);

    private void Cancel_Click(object sender, RoutedEventArgs e) => Close();

    private void Reset_Click(object sender, RoutedEventArgs e)
    {
        _loading = true;
        try
        {
            Editor.Document = PageStore.CreateStarterDocument(_bookFolder, _name, _book);
        }
        finally
        {
            _loading = false;
        }

        _dirty = true;
        StatusText.Text = "Starter text put back; save the page to keep it.";
        Editor.Focus();
    }

    /// <summary>
    /// Writes the design to its RTF file and records the file in the pages of its part of the book, so
    /// the page prints where the part belongs. Saving a page the author had taken out puts it back
    /// into the book, and a design still kept in the old <c>layout</c> folder is written into the page
    /// folder of its part instead.
    /// </summary>
    private void SavePage(bool close)
    {
        var path = FilePath;
        var moved = false;

        try
        {
            if (PageStore.IsLegacy(BookPages.Relative(ProfileBase, path)))
            {
                var folder = PageStore.GroupOf(_bookFolder, _role)?.FilePath ?? BookPages.FolderPathOf(_role);
                path = BookPages.Resolve(ProfileBase, folder + _name + BookPages.RtfExtension) ?? path;
                moved = !string.Equals(path, FilePath, StringComparison.OrdinalIgnoreCase);
            }

            RtfExport.Save(Editor, path);
            PageStore.AddFile(_bookFolder, _role, BookPages.Relative(ProfileBase, path));

            if (moved)
            {
                TryDelete(FilePath);
            }

            _dirty = false;
            Saved = true;
            StatusText.Text = $"Saved to {path}";
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException
            or ArgumentException)
        {
            StatusText.Text = $"The page could not be saved: {exception.Message}";
            MessageBox.Show(
                this,
                $"The page could not be saved.\n\n{exception.Message}",
                "Design page",
                MessageBoxButton.OK,
                MessageBoxImage.Warning);
            return;
        }

        if (close)
        {
            Close();
        }
    }

    /// <summary>Drops the old file of a design that was written into the page folders of the book.</summary>
    private static void TryDelete(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException)
        {
            // The design is saved in its page folder, so a file that cannot be dropped is only clutter.
        }
    }
}
