using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Microsoft.Win32;

using WriterWorker.Configuration;
using WriterWorker.Ctl;
using WriterWorker.Models;

namespace WriterWorker.Views;

/// <summary>
/// Asks for the layout of a PDF export - paper size and unit, font, footer, background, book layout
/// and covers - so a book can be rendered the way it is meant to be printed instead of on a fixed A4
/// sheet, and for the details the book says about itself - display name, author, price of each
/// binding, ISBN, publisher and copyright. The settings sit in tabs on the left of the window: the
/// Book Model with the details, then the parts of the book - Cover, Blurb, Publisher, Index, Content
/// and Appendix - each listing the pages designed for it, and the Print Setup last. The footer
/// reports what the dialog is busy with. Every change is written straight to the
/// <c>profile.json</c> of the book folder, so there is nothing to save by hand and a book keeps its
/// own page setup and details next to its content.
/// </summary>
public partial class PdfPageSetupDialog : Window
{
    private const string ImageFilter = "Images|*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff|All files|*.*";
    private const double MinimumMm = 25;
    private const double MaximumMm = 2000;
    private const double MinimumContentMm = 20;
    private const double MaximumMarginMm = 100;
    private const double MinimumFontSize = 4;
    private const double MaximumFontSize = 96;
    private const double PreviewExtent = 88;
    private const double MillimetresPerInch = 25.4;

    private static readonly PagePreset Custom = new("Custom - keep the size I type", double.NaN, double.NaN);

    /// <summary>
    /// Layouts offered by the dialog. The book trim sizes come first because the dialog is used to
    /// print books; 8.5 x 5.5 in - a letter sheet folded in half - is the size a book starts from.
    /// </summary>
    private static readonly PagePreset[] Presets =
    {
        new("8.5 x 5.5 in - 216 x 140 mm", 215.9, 139.7),
        new("5.5 x 8.5 in - 140 x 216 mm", 139.7, 215.9),
        new("6 x 9 in - 152 x 229 mm", 152.4, 228.6),
        new("9 x 6 in - 229 x 152 mm", 228.6, 152.4),
        new("7 x 10 in - 178 x 254 mm", 177.8, 254),
        new("A6 - 105 x 148 mm", 105, 148),
        new("A5 - 148 x 210 mm", 148, 210),
        new("B5 - 176 x 250 mm", 176, 250),
        new("A4 - 210 x 297 mm", 210, 297),
        new("Letter - 216 x 279 mm", 215.9, 279.4),
        new("Legal - 216 x 356 mm", 215.9, 355.6),
        Custom
    };

    private static readonly string[] NumberFormats =
    {
        PdfExportOptions.DefaultPageNumberFormat,
        "{page} / {total}",
        "{page} of {total}",
        "- {page} -",
        "{page}",
        "None"
    };

    private static readonly LayoutChoice[] Layouts =
    {
        new LayoutChoice(PdfLayout.ChapterPages, "Chapter pages - one page per segment"),
        new LayoutChoice(PdfLayout.Continuous, "Continuous - one flowing text")
    };

    private static readonly CoverTypeChoice[] CoverTypes =
    {
        new CoverTypeChoice(BookCoverType.Paperback, "Paperback"),
        new CoverTypeChoice(BookCoverType.HardCover, "Hard cover")
    };

    private readonly bool _showBookLayout;
    private readonly string? _bookFolder;
    private readonly string _bookName;
    private readonly DispatcherTimer _saveTimer;

    /// <summary>Folder the page paths of the profile are recorded against; the book folder when none is open.</summary>
    private string ProfileBase => _bookFolder is null ? string.Empty : BookProfile.ProfileFolderOf(_bookFolder);

    private bool _updating;
    private bool _savePending;
    private double _mmPerUnit = 1;
    private double _widthMm;
    private double _heightMm;
    private double _marginMm;

    public PdfPageSetupDialog(PdfExportOptions seed, bool showBookLayout = true, string? bookFolder = null)
    {
        InitializeComponent();

        _showBookLayout = showBookLayout;
        _bookFolder = NormalizeBookFolder(bookFolder);
        _bookName = _bookFolder is null ? string.Empty : BookLayout.BookName(_bookFolder);

        // Typing in a size box fires a change per keystroke, so the file is written once the setup
        // has stopped changing instead of on every key.
        _saveTimer = new DispatcherTimer(DispatcherPriority.Background, Dispatcher)
        {
            Interval = TimeSpan.FromMilliseconds(600)
        };

        _saveTimer.Tick += (_, _) => FlushSave();

        ConfigPathText.Text = _bookFolder is null
            ? "No book folder is open, so the setup is kept with the app settings."
            : $"Saved to {BookLayout.BookProfilePath(_bookFolder)} as the setup changes.";

        _updating = true;

        foreach (var preset in Presets)
        {
            PresetList.Items.Add(preset);
        }

        foreach (var format in NumberFormats)
        {
            FormatBox.Items.Add(format);
        }

        foreach (var layout in Layouts)
        {
            LayoutBox.Items.Add(layout);
        }

        foreach (var coverType in CoverTypes)
        {
            CoverTypeBox.Items.Add(coverType);
        }

        UnitBox.Items.Add("Millimetres (mm)");
        UnitBox.Items.Add("Inches (in)");

        LoadOptions(seed);
        LoadBookModel(seed);

        _updating = false;

        // The editable combo boxes only report selections; typing inside them has to be picked up
        // from the inner text box so the preview and the validation follow the keystrokes.
        FontBox.AddHandler(TextBoxBase.TextChangedEvent, new TextChangedEventHandler(TextField_TextChanged));
        FormatBox.AddHandler(TextBoxBase.TextChangedEvent, new TextChangedEventHandler(TextField_TextChanged));

        // The font catalog is read on a background thread so the window opens at once; Continue
        // waits for it, because every setup is validated against the catalog.
        OkButton.IsEnabled = false;
        SaveButton.IsEnabled = false;
        BeginFontIndex();
    }

    public double PageWidthMm { get; private set; }

    public double PageHeightMm { get; private set; }

    public double PageMarginMm { get; private set; }

    public string FontFamilyName { get; private set; } = PdfExport.DefaultFontFamily;

    /// <summary>Base font size in points; null keeps the size the book was written in.</summary>
    public double? FontSizePoints { get; private set; }

    public string? FooterText { get; private set; }

    public string? PageNumberFormat { get; private set; }

    public string? BackgroundImagePath { get; private set; }

    /// <summary>How the book is spread over the pages of the PDF.</summary>
    public PdfLayout Layout { get; private set; }

    /// <summary>Image printed alone on the first page of a book export.</summary>
    public string? FrontCoverImagePath { get; private set; }

    /// <summary>Image printed alone on the last page of a book export.</summary>
    public string? BackCoverImagePath { get; private set; }

    /// <summary>Whether the cover images are part of the book export.</summary>
    public bool IncludeCovers { get; private set; } = true;

    /// <summary>
    /// The details the book says about itself - display name, author, prices, ISBN, publisher and
    /// copyright - as they stand in the Book Model tab. They are stored in the <c>book</c> object of
    /// the <c>profile.json</c> of the book folder, next to the page setup.
    /// </summary>
    public BookMetadata BookModel { get; private set; } = new();

    /// <summary>
    /// Name of the profile the book is set up from, as the Select Profile tab shows it - the author,
    /// the book type and the size the book prints at - and the default profile when the book records
    /// none.
    /// </summary>
    public string ProfileName => ProfileStore.Current(_bookFolder);

    private string UnitSuffix => _mmPerUnit > 1 ? "in" : "mm";

    /// <summary>
    /// Shows the dialog on top of <paramref name="current"/> and returns the setup to export with.
    /// The accepted setup becomes <see cref="PdfExportOptions.Current"/>, so it is reused and kept
    /// for the next session. When <paramref name="bookFolder"/> is given, the setup stored in that
    /// book's <c>profile.json</c> seeds the dialog and every change made in it - or the Save button -
    /// is written back to that file, so a book keeps its own setup next to the pages it prints. A
    /// published book keeps its files inside its version folders, so the newest version is used.
    /// </summary>
    public static bool TryAsk(
        Window? owner,
        PdfExportOptions? current,
        out PdfExportOptions result,
        bool showBookLayout = true,
        string? bookFolder = null)
    {
        var seed = (current ?? PdfExportOptions.Current).Clone();
        var folder = NormalizeBookFolder(bookFolder);

        if (folder is not null && BookLayout.LoadFromBook(folder) is { } saved)
        {
            var title = seed.Title;
            var author = seed.Author;
            seed = saved.Options.Clone();
            seed.Title = title;
            seed.Author = author;
        }

        var dialog = new PdfPageSetupDialog(seed, showBookLayout, folder);
        if (owner is not null && owner.IsVisible && !ReferenceEquals(owner, dialog))
        {
            dialog.Owner = owner;
        }

        if (dialog.ShowDialog() != true)
        {
            result = seed;
            return false;
        }

        result = dialog.Apply(seed);
        PdfExportOptions.Remember(result);
        return true;
    }

    /// <summary>
    /// Writes the setup to the <c>profile.json</c> of the book folder as soon as it stops changing, so
    /// nothing has to be saved by hand. A folder that cannot be written is not worth failing the
    /// export over, so the setup is only kept globally then.
    /// </summary>
    private void ScheduleSave()
    {
        _savePending = true;
        _saveTimer.Stop();
        _saveTimer.Start();
    }

    /// <summary>Writes a change that is still waiting for the timer, such as when the dialog closes.</summary>
    private void FlushSave()
    {
        _saveTimer.Stop();

        if (!_savePending)
        {
            return;
        }

        _savePending = false;
        SaveLayout(manual: false);
    }

    /// <summary>
    /// Writes the setup to the book on request, so a folder that is shared or read-only can be told
    /// apart from one that simply has not changed yet.
    /// </summary>
    private void Save_Click(object sender, RoutedEventArgs e)
    {
        _saveTimer.Stop();
        _savePending = false;
        SaveLayout(manual: true);
    }

    /// <summary>
    /// Writes the page setup and the publishing details into the <c>profile.json</c> of the book - the
    /// file in the book folder, or the one of the newest version of a published edition - and reports
    /// where it went in the footer. A folder that cannot be written is not worth failing the export
    /// over, so the setup is only kept globally then.
    /// </summary>
    private void SaveLayout(bool manual)
    {
        var options = Apply(PdfExportOptions.Current.Clone());
        PdfExportOptions.Remember(options);

        if (_bookFolder is null)
        {
            if (manual)
            {
                ConfigPathText.Text = "No book folder is open, so there is no profile.json to save the setup to.";
            }

            return;
        }

        var path = BookLayout.BookProfilePath(_bookFolder);

        try
        {
            // The layout is saved under the name of the profile the book prints with, so the file keeps
            // naming the folder it is kept in instead of the title of the book.
            BookLayout.Create(ProfileName, options).SaveToBook(_bookFolder, BookModel);
            ConfigPathText.Text = manual
                ? $"Saved to {path} at {DateTime.Now:HH:mm:ss}."
                : $"Saved to {path} as the setup changes.";
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            ConfigPathText.Text = $"The setup could not be written to {path}: {exception.Message}";
        }
    }

    protected override void OnClosed(EventArgs e)
    {
        FlushSave();
        base.OnClosed(e);
    }

    private static string? NormalizeBookFolder(string? bookFolder)
    {
        if (string.IsNullOrWhiteSpace(bookFolder))
        {
            return null;
        }

        try
        {
            var folder = Path.GetFullPath(bookFolder);
            return Directory.Exists(folder) ? BookLayout.BookFileFolder(folder) : null;
        }
        catch (Exception exception) when (exception is ArgumentException or NotSupportedException)
        {
            return null;
        }
    }

    /// <summary>
    /// Reports work in progress in the footer. A null <paramref name="fraction"/> runs the bar
    /// without a value; <see cref="HideProgress"/> clears the footer again.
    /// </summary>
    public void ShowProgress(string? message, double? fraction = null)
    {
        ProgressText.Text = message ?? string.Empty;
        ProgressText.Visibility = string.IsNullOrEmpty(message) ? Visibility.Collapsed : Visibility.Visible;
        ProgressBar.Visibility = Visibility.Visible;
        ProgressBar.IsIndeterminate = fraction is null;
        ProgressBar.Value = fraction is null ? 0 : Math.Clamp(fraction.Value, 0, 1) * 100;
    }

    /// <summary>Clears the progress bar and the message next to it.</summary>
    public void HideProgress()
    {
        ProgressBar.Visibility = Visibility.Collapsed;
        ProgressText.Visibility = Visibility.Collapsed;
        ProgressText.Text = string.Empty;
    }

    private PdfExportOptions Apply(PdfExportOptions options)
    {
        // Sizes typed in inches land on repeating decimals once converted to millimetres, so they
        // are rounded before they reach the file the layout is written to.
        options.PageWidthMm = Math.Round(PageWidthMm, 2);
        options.PageHeightMm = Math.Round(PageHeightMm, 2);
        options.MarginMm = Math.Round(PageMarginMm, 2);
        options.SizeUnit = _mmPerUnit > 1 ? PdfSizeUnit.Inches : PdfSizeUnit.Millimetres;
        options.FontFamily = FontFamilyName;
        options.FontSize = FontSizePoints;
        options.FooterText = FooterText;
        options.PageNumberFormat = PageNumberFormat;
        options.BackgroundImagePath = BackgroundImagePath;
        options.Layout = Layout;
        options.FrontCoverImagePath = FrontCoverImagePath;
        options.BackCoverImagePath = BackCoverImagePath;
        options.IncludeCovers = IncludeCovers;
        return options;
    }

    /// <summary>Copies a setup into the controls, so a saved configuration can be loaded as well.</summary>
    private void LoadOptions(PdfExportOptions seed)
    {
        var wasUpdating = _updating;
        _updating = true;

        _mmPerUnit = seed.SizeUnit == PdfSizeUnit.Inches ? MillimetresPerInch : 1;
        UnitBox.SelectedIndex = seed.SizeUnit == PdfSizeUnit.Inches ? 1 : 0;
        UpdateUnitLabels();

        PageWidthMm = seed.PageWidthMm;
        PageHeightMm = seed.PageHeightMm;
        PageMarginMm = seed.MarginMm;
        _widthMm = PageWidthMm;
        _heightMm = PageHeightMm;
        _marginMm = PageMarginMm;
        FontFamilyName = PdfFonts.FindFamily(seed.FontFamily) ?? seed.FontFamily ?? PdfExport.DefaultFontFamily;
        FontSizePoints = seed.FontSize is > 0 ? seed.FontSize : null;
        FooterText = seed.FooterText;
        PageNumberFormat = seed.PageNumberFormat ?? PdfExportOptions.DefaultPageNumberFormat;
        BackgroundImagePath = seed.BackgroundImagePath;
        Layout = seed.Layout;

        // A workspace keeps its covers in the page folders of the book, so they stand in for the
        // images a configuration written elsewhere left out.
        var covers = PageStore.Covers(_bookFolder);
        FrontCoverImagePath = Empty(seed.FrontCoverImagePath) ?? covers.Front;
        BackCoverImagePath = covers.Back ?? Empty(seed.BackCoverImagePath);
        IncludeCovers = seed.IncludeCovers;

        WidthBox.Text = Format(PageWidthMm);
        HeightBox.Text = Format(PageHeightMm);
        MarginBox.Text = Format(PageMarginMm);
        FontBox.Text = FontFamilyName;
        SizeBox.Text = FontSizePoints is null ? string.Empty : FormatSize(FontSizePoints.Value);
        FooterBox.Text = FooterText ?? string.Empty;
        FormatBox.Text = PageNumberFormat;
        BackgroundBox.Text = BackgroundImagePath ?? string.Empty;
        FrontCoverBox.Text = FrontCoverImagePath ?? string.Empty;
        IncludeCoversBox.IsChecked = IncludeCovers;
        CoverFields.IsEnabled = IncludeCovers;

        SelectLayout(seed.Layout);
        SelectMatchingPreset(PageWidthMm, PageHeightMm);

        if (!_showBookLayout)
        {
            LayoutLabel.Visibility = Visibility.Collapsed;
            LayoutBox.Visibility = Visibility.Collapsed;
        }

        UpdatePreviews();

        _updating = wasUpdating;
    }

    /// <summary>
    /// Copies the details of the book into the Book Model tab: what the <c>profile.json</c> of the
    /// folder already holds, or what the folder and the export say about a book that has none yet.
    /// The tab and the page tabs beside it - Blurb, Publisher, Index, Content and Appendix - are
    /// only shown for a book folder, because the details and the page designs are kept with the book.
    /// </summary>
    private void LoadBookModel(PdfExportOptions seed)
    {
        var withBook = _bookFolder is null ? Visibility.Collapsed : Visibility.Visible;

        BookModelTab.Visibility = withBook;
        BlurbTab.Visibility = withBook;
        PublisherTab.Visibility = withBook;
        IndexTab.Visibility = withBook;
        ContentTab.Visibility = withBook;
        AppendixTab.Visibility = withBook;
        BackCoverTab.Visibility = withBook;

        // The profile the book is set up from opens first, because it is what the rest of the window
        // describes: the shape of the book the details and the pages belong to.
        LoadProfiles();
        SetupTabs.SelectedItem = _bookFolder is null ? PdfSetupTab : ProfileTab;

        BookModel = BookLayout.LoadBook(_bookFolder) ?? new BookMetadata();
        BookModel.DisplayName ??= Empty(_bookName);
        BookModel.Author ??= Empty(seed.Author);
        BookModel.YearOfProduction ??= DateTime.Now.Year;

        DisplayNameBox.Text = BookModel.DisplayName ?? string.Empty;
        AuthorBox.Text = BookModel.Author ?? string.Empty;
        AboutAuthorBox.Text = BookModel.AboutAuthor ?? string.Empty;
        AboutBookBox.Text = BookModel.AboutBook ?? string.Empty;
        PaperbackPriceBox.Text = FormatPrice(BookModel.PaperbackPrice);
        HardCoverPriceBox.Text = FormatPrice(BookModel.HardCoverPrice);
        IsbnBox.Text = BookModel.Isbn ?? string.Empty;
        PublisherBox.Text = BookModel.PublisherName ?? string.Empty;
        PublisherAddressBox.Text = BookModel.PublisherAddress ?? string.Empty;
        PublisherLogoBox.Text = BookModel.PublisherLogoPath ?? string.Empty;
        ComposerBox.Text = BookModel.Composer ?? string.Empty;
        CoverArtistBox.Text = BookModel.CoverArtist ?? string.Empty;
        YearBox.Text = BookModel.YearOfProduction is { } year
            ? year.ToString(CultureInfo.CurrentCulture)
            : string.Empty;
        CopyrightBox.Text = BookModel.Copyright ?? string.Empty;

        SelectCoverType(BookModel.CoverType);
        LoadPages();
    }

    /// <summary>
    /// Fills the Select Profile tab with the profiles kept in the settings folder and selects the one
    /// the book was set up from - the default profile when the book records none - so the tab opens on
    /// the shape the book prints at. The profiles are read again on every visit to the tab, so a
    /// profile edited in the settings folder is listed as it is now.
    /// </summary>
    private void LoadProfiles()
    {
        var profiles = ProfileStore.Catalog(_bookFolder);

        var wasUpdating = _updating;
        _updating = true;

        try
        {
            ProfileList.ItemsSource = profiles;
            ProfileList.SelectedItem = profiles.FirstOrDefault(profile => profile.InUse)
                ?? profiles.FirstOrDefault(profile => profile.IsDefault)
                ?? profiles.FirstOrDefault();
        }
        finally
        {
            _updating = wasUpdating;
        }

        ShowProfile(ProfileList.SelectedItem as ProfileInfo);
    }

    /// <summary>Describes the profile selected in the list, so the author, the type and the size it is for can be read before it is used.</summary>
    private void ShowProfile(ProfileInfo? profile)
    {
        ApplyProfileButton.IsEnabled = _bookFolder is not null && profile is not null;

        if (profile is null)
        {
            ProfileSummaryText.Text = $"No profile is kept in {ProfileStore.Folder} yet.";
            return;
        }

        ProfileSummaryText.Text = string.Join(
            Environment.NewLine,
            $"{profile.Name} - {profile.Details}",
            $"Kept in {ProfileStore.PathOf(profile.Name)}");
    }

    private void ProfileList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_updating)
        {
            return;
        }

        ShowProfile(ProfileList.SelectedItem as ProfileInfo);
    }

    private void RefreshProfiles_Click(object sender, RoutedEventArgs e) => LoadProfiles();

    private void OpenProfileFolder_Click(object sender, RoutedEventArgs e)
    {
        var folder = ProfileStore.Ensure();

        try
        {
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = folder,
                UseShellExecute = true
            });
        }
        catch (Exception exception) when (exception is InvalidOperationException
            or System.ComponentModel.Win32Exception
            or IOException)
        {
            MessageText.Text = $"The profile folder could not be opened: {exception.Message}";
        }
    }

    /// <summary>
    /// Sets the book up from the profile selected in the list: the profile is recorded in the
    /// configuration of the book and whatever the book does not have yet - its configuration or the
    /// pages of the profile - is copied into it. The page tabs are read again, so the pages the book
    /// started with are seen where they print.
    /// </summary>
    private void ApplyProfile_Click(object sender, RoutedEventArgs e)
    {
        if (_bookFolder is null || ProfileList.SelectedItem is not ProfileInfo profile)
        {
            return;
        }

        FlushSave();

        bool copied;

        try
        {
            copied = ProfileStore.Apply(_bookFolder, profile.Name);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The {profile.Name} profile could not be applied: {exception.Message}";
            return;
        }

        MessageText.Text = copied
            ? $"The book was set up from the {profile.Name} profile."
            : $"The book follows the {profile.Name} profile; its pages were not copied because the book already has pages of its own.";

        LoadPages();
        SyncCovers();
        LoadProfiles();
    }


    /// <summary>
    /// Fills the page lists of the Cover, Blurb, Publisher, Index, Content, Appendix and Back Cover
    /// tabs from the <c>pages</c> section of the book folder: every page of a part of the book under
    /// the tab of that part, in the order it prints. Only the pages the configuration records are
    /// listed, so a tab shows the book as it is; the pages a part could still be given are added with
    /// "Insert page", "Insert blank page" or "Create missing pages" instead of being listed as rows
    /// that print nothing.
    /// </summary>
    private void LoadPages()
    {
        var groups = PageStore.Load(_bookFolder);

        CoverPageList.ItemsSource = PagesOf(groups, PageGroupRole.Cover);
        BlurbPageList.ItemsSource = PagesOf(groups, PageGroupRole.Blurb);
        PublisherPageList.ItemsSource = PagesOf(groups, PageGroupRole.Publisher);
        IndexPageList.ItemsSource = PagesOf(groups, PageGroupRole.Index);
        ContentPageList.ItemsSource = PagesOf(groups, PageGroupRole.Content);
        AppendixPageList.ItemsSource = PagesOf(groups, PageGroupRole.Appendix);
        BackCoverPageList.ItemsSource = PagesOf(groups, PageGroupRole.BackCover);
    }

    /// <summary>The pages of one part of the book: the ones its folder records, in print order.</summary>
    private List<PageItem> PagesOf(IReadOnlyList<BookPageGroup> groups, PageGroupRole role)
    {
        var items = new List<PageItem>();

        if (_bookFolder is null)
        {
            return items;
        }

        var group = groups.FirstOrDefault(candidate => candidate.Role == role);
        var designs = BookPages.DesignNamesOf(role);

        foreach (var file in group?.Printed ?? Enumerable.Empty<BookPageFile>())
        {
            var exists = BookPages.Resolve(ProfileBase, file.FilePath) is { } path && File.Exists(path);

            // A page recorded in the book says whether it was written: "Not designed" when it is one
            // of the designs of the part and its file is not there yet, "File missing" for any other
            // page, whose file has gone since it was designed.
            var state = exists
                ? "Designed"
                : designs.Contains(file.Name, StringComparer.OrdinalIgnoreCase)
                    ? "Not designed"
                    : "File missing";

            items.Add(PageItem.Of(role, file.FilePath, BookPages.DisplayNameOfFile(file.FilePath), state));
        }

        // Every row keeps both arrows; the ones a page cannot use - the first page has nothing above
        // it, the last nothing below - are greyed out so the rows do not change shape.
        for (var index = 0; index < items.Count; index++)
        {
            items[index].Movable(index > 0, index < items.Count - 1);
        }

        return items;
    }

    private void DesignPage_Click(object sender, RoutedEventArgs e)
    {
        if (_bookFolder is null || sender is not FrameworkElement { Tag: PageItem item })
        {
            return;
        }

        FlushSave();

        var designer = new PageDesignerWindow(
            _bookFolder,
            item.Role,
            item.FileName,
            Apply(PdfExportOptions.Current.Clone()),
            BookModel)
        {
            Owner = this
        };

        designer.ShowDialog();
        LoadPages();
    }

    /// <summary>
    /// Takes a page out of the book by dropping it from the <c>paths</c> of its page folder, so it
    /// stops printing. The file is left on disk, so the page can be put back by designing it again.
    /// </summary>
    private void ClearPage_Click(object sender, RoutedEventArgs e)
    {
        if (_bookFolder is null || sender is not FrameworkElement { Tag: PageItem item })
        {
            return;
        }

        try
        {
            PageStore.RemoveFile(_bookFolder, item.Role, item.RelativePath);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The page could not be taken out of the book: {exception.Message}";
            return;
        }

        LoadPages();
    }

    /// <summary>Prints the page one place earlier in the book.</summary>
    private void MovePageUp_Click(object sender, RoutedEventArgs e) => MovePage(sender, -1);

    /// <summary>Prints the page one place later in the book.</summary>
    private void MovePageDown_Click(object sender, RoutedEventArgs e) => MovePage(sender, 1);

    /// <summary>
    /// Trades the page with the one above or below it in its list, so the order the list shows is the
    /// order the pages print in. The page keeps the selection, so the arrows can be pressed again.
    /// </summary>
    private void MovePage(object sender, int offset)
    {
        if (_bookFolder is null || sender is not FrameworkElement { Tag: PageItem item })
        {
            return;
        }

        FlushSave();

        try
        {
            PageStore.MoveFile(_bookFolder, item.Role, item.RelativePath, offset);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The order of the pages could not be written: {exception.Message}";
            return;
        }

        LoadPages();
        Select(item.Role, item.RelativePath);
        MessageText.Text = $"{item.Name} now prints at place {PlaceOf(item)} of the {BookPages.DisplayNameOf(item.Role)} pages.";
    }

    /// <summary>
    /// Deletes a page of the book: it is taken out of the pages and its file is deleted from the
    /// workspace, which is more than "Don't print" does, so the author is asked first.
    /// </summary>
    private void DeletePage_Click(object sender, RoutedEventArgs e)
    {
        if (_bookFolder is null || sender is not FrameworkElement { Tag: PageItem item })
        {
            return;
        }

        var answer = MessageBox.Show(
            this,
            $"Delete the {item.Name} of the book?\r\n\r\n"
                + $"The page is taken out of the book and {item.RelativePath} is deleted from the workspace. "
                + "Use \"Don't print\" to take the page out of the book and keep the file.",
            "Delete page",
            MessageBoxButton.OKCancel,
            MessageBoxImage.Warning,
            MessageBoxResult.Cancel);

        if (answer != MessageBoxResult.OK)
        {
            return;
        }

        FlushSave();

        try
        {
            PageStore.DeleteFile(_bookFolder, item.Role, item.RelativePath);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The page could not be deleted: {exception.Message}";
            return;
        }

        LoadPages();
        MessageText.Text = $"{item.Name} was deleted from the book.";
    }

    /// <summary>
    /// Adds a page to the part of the book the button belongs to, where the page selected in its list
    /// is: a cover image is picked and copied into the cover folder, and the other parts are given the
    /// design they are missing - a dedication, a copyright page, a foreword - written with the details
    /// of the book, so a page can be put between the ones a part already has instead of at their end.
    /// </summary>
    private void InsertPage_Click(object sender, RoutedEventArgs e)
    {
        if (_bookFolder is null || !RoleOf((sender as FrameworkElement)?.Tag, out var role))
        {
            return;
        }

        FlushSave();

        var position = InsertPosition(role);

        if (BookPages.FormatOf(role) == PageFormat.Image)
        {
            InsertImage(role, position);
            return;
        }

        var folder = PageStore.GroupOf(_bookFolder, role)?.FilePath ?? BookPages.FolderPathOf(role);
        var name = PageStore.NextDesignName(_bookFolder, role);
        var relative = folder + name + BookPages.RtfExtension;

        try
        {
            if (BookPages.Resolve(ProfileBase, relative) is { } design)
            {
                PageStore.WriteStarter(_bookFolder, design, name, BookModel);
            }

            PageStore.InsertFile(_bookFolder, role, relative, position);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The page could not be added to {PageStore.FolderIn(_bookFolder)}: {exception.Message}";
            return;
        }

        LoadPages();
        Select(role, relative);
        MessageText.Text = $"{BookPages.DisplayNameOfFile(relative)} was added to the {BookPages.DisplayNameOf(role)} pages; design it to write it.";
    }

    /// <summary>
    /// Adds a blank page to the part of the book the button belongs to, where the page selected in its
    /// list is: an empty design is written to the folder of the part and recorded with the pages, so an
    /// empty sheet can be kept between the pages a part already has - after the chapters, before the
    /// appendix, at the end of the book - instead of only at the end of the part. The sheet is printed
    /// blank by the export, and it is an ordinary page of the folder, so it can be designed or deleted
    /// like any other.
    /// </summary>
    private void InsertBlankPage_Click(object sender, RoutedEventArgs e)
    {
        if (_bookFolder is null || !RoleOf((sender as FrameworkElement)?.Tag, out var role))
        {
            return;
        }

        FlushSave();

        var position = InsertPosition(role);
        string relative;

        try
        {
            (_, relative) = PageStore.InsertBlank(_bookFolder, role, position);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The blank page could not be added to {PageStore.FolderIn(_bookFolder)}: {exception.Message}";
            return;
        }

        LoadPages();
        Select(role, relative);
        MessageText.Text = $"A blank page was added to the {BookPages.DisplayNameOf(role)} pages; it prints as an empty sheet and can be designed like any other page.";
    }

    /// <summary>
    /// Copies an image the author picks into the folder of <paramref name="role"/> and prints it where
    /// the selected page of that part is, so an image can be put between the pages a part already has
    /// instead of after them.
    /// </summary>
    private void InsertImage(PageGroupRole role, int position)
    {
        if (_bookFolder is null)
        {
            return;
        }

        var picker = new OpenFileDialog
        {
            Title = $"Insert {BookPages.DisplayNameOf(role).ToLowerInvariant()} image",
            Filter = ImageFilter,
            Multiselect = false,
            InitialDirectory = Directory.Exists(PageStore.FolderIn(_bookFolder))
                ? PageStore.FolderIn(_bookFolder)
                : _bookFolder
        };

        if (picker.ShowDialog(this) != true)
        {
            return;
        }

        var folder = PageStore.GroupOf(_bookFolder, role)?.FilePath ?? BookPages.FolderPathOf(role);

        string? relative = null;

        try
        {
            if (BookPages.Resolve(ProfileBase, folder + Path.GetFileName(picker.FileName)) is not { } target)
            {
                return;
            }

            var parent = Path.GetDirectoryName(target)!;
            Directory.CreateDirectory(parent);

            if (File.Exists(target)
                && !string.Equals(Path.GetFullPath(picker.FileName), target, StringComparison.OrdinalIgnoreCase))
            {
                target = FreeName(parent, Path.GetFileName(picker.FileName));
            }

            if (!string.Equals(Path.GetFullPath(picker.FileName), target, StringComparison.OrdinalIgnoreCase))
            {
                File.Copy(picker.FileName, target);
            }

            relative = BookPages.Relative(ProfileBase, target);
            PageStore.InsertFile(_bookFolder, role, relative, position);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The image could not be copied into the book: {exception.Message}";
        }

        SyncCovers();
        LoadPages();

        if (relative is not null)
        {
            Select(role, relative);
            MessageText.Text = $"{BookPages.DisplayNameOfFile(relative)} was added to the {BookPages.DisplayNameOf(role).ToLowerInvariant()} pages.";
        }
    }

    /// <summary>
    /// Copies the images the author picks into the folder of <paramref name="role"/> and records them
    /// in the pages of the book, so the part prints without the book having to point at a picture kept
    /// elsewhere.
    /// </summary>
    private void AddImages(PageGroupRole role)
    {
        if (_bookFolder is null)
        {
            return;
        }

        var picker = new OpenFileDialog
        {
            Title = $"Add {BookPages.DisplayNameOf(role).ToLowerInvariant()} images",
            Filter = ImageFilter,
            Multiselect = true,
            InitialDirectory = Directory.Exists(PageStore.FolderIn(_bookFolder))
                ? PageStore.FolderIn(_bookFolder)
                : _bookFolder
        };

        if (picker.ShowDialog(this) != true)
        {
            return;
        }

        var folder = PageStore.GroupOf(_bookFolder, role)?.FilePath ?? BookPages.FolderPathOf(role);

        try
        {
            foreach (var source in picker.FileNames)
            {
                if (BookPages.Resolve(ProfileBase, folder + Path.GetFileName(source)) is not { } target)
                {
                    continue;
                }

                Directory.CreateDirectory(Path.GetDirectoryName(target)!);

                if (!string.Equals(Path.GetFullPath(source), target, StringComparison.OrdinalIgnoreCase)
                    && !File.Exists(target))
                {
                    File.Copy(source, target);
                }

                PageStore.AddFile(_bookFolder, role, BookPages.Relative(ProfileBase, target));
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The {BookPages.DisplayNameOf(role).ToLowerInvariant()} images could not be copied into the book: {exception.Message}";
        }

        SyncCovers();
        LoadPages();
    }

    /// <summary>
    /// Copies the cover images the author picks into the cover folder of the book and records them in
    /// its pages, so the covers print without the book having to point at a picture kept elsewhere.
    /// </summary>
    private void AddCoverImages_Click(object sender, RoutedEventArgs e) => AddImages(PageGroupRole.Cover);

    /// <summary>Copies back cover images into the back cover folder and prints them at the end of the book.</summary>
    private void AddBackCoverImages_Click(object sender, RoutedEventArgs e) => AddImages(PageGroupRole.BackCover);

    /// <summary>
    /// The cover box of the Print Setup follows the pages of the book, so a cover just added is
    /// offered as the front cover without being browsed for again. The back cover needs no box of its
    /// own: it is printed from the pages of the Back Cover tab, and the export reads it from there.
    /// </summary>
    private void SyncCovers()
    {
        if (_bookFolder is null)
        {
            return;
        }

        var covers = PageStore.Covers(_bookFolder);
        FrontCoverImagePath = covers.Front ?? FrontCoverImagePath;
        BackCoverImagePath = covers.Back ?? BackCoverImagePath;
        FrontCoverBox.Text = FrontCoverImagePath ?? string.Empty;
        UpdatePreviews();
    }

    /// <summary>The first name in <paramref name="folder"/> that <paramref name="fileName"/> can be copied to.</summary>
    private static string FreeName(string folder, string fileName)
    {
        var stem = Path.GetFileNameWithoutExtension(fileName);
        var extension = Path.GetExtension(fileName);

        for (var number = 2; ; number++)
        {
            var candidate = Path.Combine(folder, $"{stem}-{number}{extension}");

            if (!File.Exists(candidate))
            {
                return candidate;
            }
        }
    }

    /// <summary>
    /// The place in the pages of <paramref name="role"/> a page is inserted at: after the page
    /// selected in its list, or at the end of the part when nothing is selected.
    /// </summary>
    private int InsertPosition(PageGroupRole role)
    {
        var pages = PageStore.GroupOf(_bookFolder, role)?.Printed.ToList() ?? [];

        if (ListOf(role)?.SelectedItem is PageItem selected)
        {
            var index = pages.FindIndex(file => BookPages.SamePath(file.FilePath, selected.RelativePath));

            if (index >= 0)
            {
                return index + 2;
            }
        }

        return pages.Count + 1;
    }

    /// <summary>Where in the pages of its part a page prints, counted from one.</summary>
    private int PlaceOf(PageItem item) =>
        (PageStore.GroupOf(_bookFolder, item.Role)?.Printed.ToList() ?? [])
            .FindIndex(file => BookPages.SamePath(file.FilePath, item.RelativePath)) + 1;

    /// <summary>The list a part of the book is shown in.</summary>
    private ListBox? ListOf(PageGroupRole role) => role switch
    {
        PageGroupRole.Cover => CoverPageList,
        PageGroupRole.Blurb => BlurbPageList,
        PageGroupRole.Publisher => PublisherPageList,
        PageGroupRole.Index => IndexPageList,
        PageGroupRole.Content => ContentPageList,
        PageGroupRole.Appendix => AppendixPageList,
        PageGroupRole.BackCover => BackCoverPageList,
        _ => null
    };

    /// <summary>Selects the page of <paramref name="role"/> kept in <paramref name="relativePath"/>, so a page that moved is seen where it went.</summary>
    private void Select(PageGroupRole role, string relativePath)
    {
        if (ListOf(role) is not { } list)
        {
            return;
        }

        if (list.Items.OfType<PageItem>()
            .FirstOrDefault(item => BookPages.SamePath(item.RelativePath, relativePath)) is { } item)
        {
            list.SelectedItem = item;
            list.ScrollIntoView(item);
        }
    }

    private void CreatePages_Click(object sender, RoutedEventArgs e)
    {
        if (_bookFolder is null || !RoleOf((sender as FrameworkElement)?.Tag, out var role))
        {
            return;
        }

        try
        {
            PageStore.EnsureDesigns(_bookFolder, role, BookModel);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            MessageText.Text = $"The pages could not be written to {PageStore.FolderIn(_bookFolder)}: {exception.Message}";
            return;
        }

        LoadPages();
    }

    /// <summary>
    /// Reads the part of the book a "Create missing pages" button works on from its tag, which names
    /// it the way <see cref="PageGroupRole"/> does.
    /// </summary>
    private static bool RoleOf(object? tag, out PageGroupRole role)
    {
        role = PageGroupRole.Other;

        return tag is string text
            && Enum.TryParse(text.Trim(), ignoreCase: true, out role)
            && role != PageGroupRole.Other;
    }

    private void UpdateUnitLabels()
    {
        WidthLabel.Text = $"Width ({UnitSuffix})";
        HeightLabel.Text = $"Height ({UnitSuffix})";
        MarginLabel.Text = $"Margin ({UnitSuffix})";
    }

    private void BeginFontIndex()
    {
        ShowProgress("Reading the installed fonts...");

        Task.Run(() => PdfFonts.Instance.FamilyNames).ContinueWith(
            task =>
            {
                if (Dispatcher.HasShutdownStarted || Dispatcher.HasShutdownFinished)
                {
                    return;
                }

                try
                {
                    Dispatcher.BeginInvoke(new Action(() => CompleteFontIndex(task)));
                }
                catch (TaskCanceledException)
                {
                    // The application is shutting down; nothing is left to fill in.
                }
            },
            TaskScheduler.Default);
    }

    private void CompleteFontIndex(Task<IReadOnlyList<string>> task)
    {
        if (task.Status == TaskStatus.RanToCompletion)
        {
            var text = FontBox.Text;
            foreach (var family in task.Result)
            {
                FontBox.Items.Add(family);
            }

            FontBox.Text = text;
        }

        HideProgress();
        Update();
    }

    private void UnitBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_updating)
        {
            return;
        }

        var mmPerUnit = UnitBox.SelectedIndex == 1 ? MillimetresPerInch : 1;
        if (Math.Abs(mmPerUnit - _mmPerUnit) < 0.001)
        {
            return;
        }

        _mmPerUnit = mmPerUnit;

        _updating = true;
        WidthBox.Text = Format(_widthMm);
        HeightBox.Text = Format(_heightMm);
        MarginBox.Text = Format(_marginMm);
        _updating = false;

        UpdateUnitLabels();
        Update();
    }

    private void PresetList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_updating || PresetList.SelectedItem is not PagePreset preset || preset.IsCustom)
        {
            return;
        }

        _updating = true;
        _widthMm = preset.WidthMm;
        _heightMm = preset.HeightMm;
        WidthBox.Text = Format(_widthMm);
        HeightBox.Text = Format(_heightMm);
        _updating = false;

        Update();
    }

    private void SizeBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (_updating)
        {
            return;
        }

        if (TryReadSize(out var width, out var height, out var margin, out _))
        {
            _widthMm = width;
            _heightMm = height;
            _marginMm = margin;
            SelectMatchingPreset(width, height);
        }

        Update();
    }

    private void TextField_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (!_updating)
        {
            Update();
        }
    }

    private void TextField_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_updating)
        {
            Update();
        }
    }

    private void IncludeCovers_Changed(object sender, RoutedEventArgs e)
    {
        CoverFields.IsEnabled = IncludeCoversBox.IsChecked == true;

        if (!_updating)
        {
            Update();
        }
    }

    private void BrowseBackground_Click(object sender, RoutedEventArgs e)
        => BrowseImage(BackgroundBox, "Choose a background image");

    private void ClearBackground_Click(object sender, RoutedEventArgs e) => BackgroundBox.Text = string.Empty;

    private void BrowseFrontCover_Click(object sender, RoutedEventArgs e)
        => BrowseImage(FrontCoverBox, "Choose the front cover image");

    private void ClearFrontCover_Click(object sender, RoutedEventArgs e) => FrontCoverBox.Text = string.Empty;

    private void BrowsePublisherLogo_Click(object sender, RoutedEventArgs e)
        => BrowseImage(PublisherLogoBox, "Choose the publisher logo image");

    private void ClearPublisherLogo_Click(object sender, RoutedEventArgs e) => PublisherLogoBox.Text = string.Empty;

    private void BrowseImage(TextBox box, string title)
    {
        var dialog = new OpenFileDialog
        {
            Title = title,
            Filter = ImageFilter,
            CheckFileExists = true
        };

        var current = box.Text?.Trim();
        if (!string.IsNullOrEmpty(current) && File.Exists(current))
        {
            dialog.FileName = current;
        }

        if (dialog.ShowDialog(this) == true)
        {
            box.Text = dialog.FileName;
        }
    }

    private void Ok_Click(object sender, RoutedEventArgs e)
    {
        FlushSave();
        DialogResult = true;
    }

    private void Update()
    {
        UpdatePreviews();

        var valid = TryRead(out var width, out var height, out var margin, out var message);

        MessageText.Text = message;
        OkButton.IsEnabled = valid;
        SaveButton.IsEnabled = valid && _bookFolder is not null;

        if (!valid)
        {
            return;
        }

        PageWidthMm = width;
        PageHeightMm = height;
        PageMarginMm = margin;

        var scale = PreviewExtent / Math.Max(width, height);
        PreviewBox.Width = Math.Max(12, width * scale);
        PreviewBox.Height = Math.Max(12, height * scale);

        ScheduleSave();
    }

    private bool TryRead(out double width, out double height, out double margin, out string message)
    {
        width = 0;
        height = 0;
        margin = 0;
        message = "Choose how every page of the PDF is rendered.";

        if (!TryReadSize(out width, out height, out margin, out message))
        {
            return false;
        }

        var family = FontBox.Text?.Trim() ?? string.Empty;
        if (family.Length == 0)
        {
            family = PdfExport.DefaultFontFamily;
        }

        var resolved = PdfFonts.FindFamily(family);
        if (resolved is null)
        {
            message = $"The font \"{family}\" is not installed; choose another one.";
            return false;
        }

        var sizeText = SizeBox.Text?.Trim() ?? string.Empty;
        double? size = null;
        if (sizeText.Length > 0)
        {
            if (!TryParse(sizeText, out var value) || value is < MinimumFontSize or > MaximumFontSize)
            {
                message = $"The font size must be a number between {MinimumFontSize:0} and {MaximumFontSize:0} points, or empty.";
                return false;
            }

            size = value;
        }

        var background = BackgroundBox.Text?.Trim();
        if (!string.IsNullOrEmpty(background) && !File.Exists(background))
        {
            message = "The background image file was not found.";
            return false;
        }

        var includeCovers = IncludeCoversBox.IsChecked == true;
        var frontCover = Empty(FrontCoverBox.Text);

        // The back cover is a page of the book like any other, so it is read from the Back Cover tab
        // instead of a box of its own; a book without a back cover page has no back cover to print.
        var backCover = _bookFolder is null
            ? Empty(BackCoverImagePath)
            : PageStore.Covers(_bookFolder).Back;

        if (includeCovers)
        {
            if (frontCover is not null && !File.Exists(frontCover))
            {
                message = "The front cover image file was not found.";
                return false;
            }

            if (backCover is not null && !File.Exists(backCover))
            {
                message = "The back cover image file was not found.";
                return false;
            }
        }

        if (!TryReadBookModel(out message))
        {
            return false;
        }

        FontFamilyName = resolved;
        FontSizePoints = size;
        FooterText = Empty(FooterBox.Text);
        PageNumberFormat = FormatBox.Text?.Trim() ?? string.Empty;
        BackgroundImagePath = Empty(background);
        FrontCoverImagePath = frontCover;
        BackCoverImagePath = backCover;
        IncludeCovers = includeCovers;

        if (LayoutBox.SelectedItem is LayoutChoice layout)
        {
            Layout = layout.Layout;
        }

        var sizeLabel = size is null ? "the size of the book" : $"{FormatSize(size.Value)} pt";
        message = $"{Format(width)} x {Format(height)} {UnitSuffix} page, {Format(margin)} {UnitSuffix} margin, {resolved} at {sizeLabel}";

        if (includeCovers)
        {
            var covers = new List<string>();
            if (frontCover is not null)
            {
                covers.Add("front cover");
            }

            if (backCover is not null)
            {
                covers.Add("back cover");
            }

            if (covers.Count > 0)
            {
                message += $", with a {string.Join(" and a ", covers)}";
            }
        }

        message += ".";
        return true;
    }

    /// <summary>
    /// Reads the Book Model tab into <see cref="BookModel"/>. A price has to be a number and the year
    /// of production a whole year, so a typo is reported in the footer instead of being written to
    /// the configuration of the book.
    /// </summary>
    private bool TryReadBookModel(out string message)
    {
        message = string.Empty;

        if (!TryParsePrice(PaperbackPriceBox.Text, out var paperbackPrice))
        {
            message = "The paperback price must be a number, or empty.";
            return false;
        }

        if (!TryParsePrice(HardCoverPriceBox.Text, out var hardCoverPrice))
        {
            message = "The hard cover price must be a number, or empty.";
            return false;
        }

        int? year = null;
        var yearText = YearBox.Text?.Trim() ?? string.Empty;
        if (yearText.Length > 0)
        {
            if (!int.TryParse(yearText, NumberStyles.Integer, CultureInfo.CurrentCulture, out var value)
                && !int.TryParse(yearText, NumberStyles.Integer, CultureInfo.InvariantCulture, out value))
            {
                message = "The year of production must be a whole number, or empty.";
                return false;
            }

            if (value is < 1000 or > 3000)
            {
                message = "The year of production must be a year between 1000 and 3000.";
                return false;
            }

            year = value;
        }

        var logo = Empty(PublisherLogoBox.Text);
        if (logo is not null && !File.Exists(logo))
        {
            message = "The publisher logo file was not found.";
            return false;
        }

        BookModel.DisplayName = Empty(DisplayNameBox.Text);
        BookModel.Author = Empty(AuthorBox.Text);
        BookModel.AboutAuthor = Empty(AboutAuthorBox.Text);
        BookModel.AboutBook = Empty(AboutBookBox.Text);
        BookModel.CoverType = CoverTypeBox.SelectedItem is CoverTypeChoice coverType
            ? coverType.CoverType
            : BookCoverType.Paperback;
        BookModel.PaperbackPrice = paperbackPrice;
        BookModel.HardCoverPrice = hardCoverPrice;
        BookModel.Isbn = Empty(IsbnBox.Text);
        BookModel.PublisherName = Empty(PublisherBox.Text);
        BookModel.PublisherAddress = Empty(PublisherAddressBox.Text);
        BookModel.PublisherLogoPath = logo;
        BookModel.Composer = Empty(ComposerBox.Text);
        BookModel.CoverArtist = Empty(CoverArtistBox.Text);
        BookModel.YearOfProduction = year;
        BookModel.Copyright = Empty(CopyrightBox.Text);
        return true;
    }

    private bool TryReadSize(out double width, out double height, out double margin, out string message)
    {
        width = 0;
        height = 0;
        margin = 0;
        message = string.Empty;

        if (!TryParse(WidthBox.Text, out var widthValue) || !TryParse(HeightBox.Text, out var heightValue))
        {
            message = "Enter a number for the width and the height.";
            return false;
        }

        width = widthValue * _mmPerUnit;
        height = heightValue * _mmPerUnit;

        if (width is < MinimumMm or > MaximumMm || height is < MinimumMm or > MaximumMm)
        {
            message = $"Width and height must be between {Format(MinimumMm)} and {Format(MaximumMm)} {UnitSuffix}.";
            return false;
        }

        if (!TryParse(MarginBox.Text, out var marginValue))
        {
            message = "Enter a number for the margin.";
            return false;
        }

        margin = marginValue * _mmPerUnit;
        if (margin is < 0 or > MaximumMarginMm)
        {
            message = $"The margin must be between 0 and {Format(MaximumMarginMm)} {UnitSuffix}.";
            return false;
        }

        if (width - (2 * margin) < MinimumContentMm || height - (2 * margin) < MinimumContentMm)
        {
            message = $"The margin leaves less than {Format(MinimumContentMm)} {UnitSuffix} of content; use a smaller margin.";
            return false;
        }

        return true;
    }

    private void UpdatePreviews()
    {
        FrontCoverPreview.Source = LoadPreview(Empty(FrontCoverBox.Text));
        PublisherLogoPreview.Source = LoadPreview(Empty(PublisherLogoBox.Text));
    }

    private static BitmapImage? LoadPreview(string? path)
    {
        if (path is null || !File.Exists(path))
        {
            return null;
        }

        try
        {
            var image = new BitmapImage();
            image.BeginInit();
            image.CacheOption = BitmapCacheOption.OnLoad;
            image.CreateOptions = BitmapCreateOptions.IgnoreImageCache;
            image.DecodePixelWidth = 192;
            image.UriSource = new Uri(path, UriKind.Absolute);
            image.EndInit();
            image.Freeze();
            return image;
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException
            or UriFormatException
            or ArgumentException)
        {
            return null;
        }
    }

    private void SelectMatchingPreset(double width, double height)
    {
        var match = Presets.FirstOrDefault(preset => !preset.IsCustom
            && Math.Abs(preset.WidthMm - width) < 0.5
            && Math.Abs(preset.HeightMm - height) < 0.5) ?? Custom;

        var wasUpdating = _updating;
        _updating = true;
        PresetList.SelectedItem = match;
        PresetList.ScrollIntoView(match);
        _updating = wasUpdating;
    }

    private void SelectLayout(PdfLayout layout)
    {
        var wasUpdating = _updating;
        _updating = true;
        LayoutBox.SelectedItem = Layouts.FirstOrDefault(choice => choice.Layout == layout) ?? Layouts[0];
        _updating = wasUpdating;
    }

    private void SelectCoverType(BookCoverType coverType)
    {
        var wasUpdating = _updating;
        _updating = true;
        CoverTypeBox.SelectedItem =
            CoverTypes.FirstOrDefault(choice => choice.CoverType == coverType) ?? CoverTypes[0];
        _updating = wasUpdating;
    }

    private static string? Empty(string? text)
    {
        var trimmed = text?.Trim();
        return string.IsNullOrEmpty(trimmed) ? null : trimmed;
    }

    private static bool TryParse(string? text, out double value)
    {
        var trimmed = (text ?? string.Empty).Trim();
        return double.TryParse(trimmed, NumberStyles.Float, CultureInfo.CurrentCulture, out value)
            || double.TryParse(trimmed, NumberStyles.Float, CultureInfo.InvariantCulture, out value);
    }

    private static string FormatSize(double points) => points.ToString("0.##", CultureInfo.CurrentCulture);

    private static string FormatPrice(decimal? price) =>
        price is { } value ? value.ToString("0.##", CultureInfo.CurrentCulture) : string.Empty;

    /// <summary>Reads a price; an empty box means the edition is not sold on its own.</summary>
    private static bool TryParsePrice(string? text, out decimal? price)
    {
        price = null;

        var trimmed = (text ?? string.Empty).Trim();
        if (trimmed.Length == 0)
        {
            return true;
        }

        if (!decimal.TryParse(trimmed, NumberStyles.Number, CultureInfo.CurrentCulture, out var value)
            && !decimal.TryParse(trimmed, NumberStyles.Number, CultureInfo.InvariantCulture, out value))
        {
            return false;
        }

        if (value < 0)
        {
            return false;
        }

        price = value;
        return true;
    }

    /// <summary>Formats a value given in millimetres in the unit currently shown by the dialog.</summary>
    private string Format(double millimetres) => (millimetres / _mmPerUnit).ToString("0.##", CultureInfo.CurrentCulture);

    private sealed class PagePreset
    {
        public PagePreset(string name, double widthMm, double heightMm)
        {
            Name = name;
            WidthMm = widthMm;
            HeightMm = heightMm;
        }

        public string Name { get; }

        public double WidthMm { get; }

        public double HeightMm { get; }

        public bool IsCustom => double.IsNaN(WidthMm);

        public override string ToString() => Name;
    }

    /// <summary>One entry of the layout list.</summary>
    private sealed class LayoutChoice
    {
        public LayoutChoice(PdfLayout layout, string name)
        {
            Layout = layout;
            Name = name;
        }

        public PdfLayout Layout { get; }

        public string Name { get; }

        public override string ToString() => Name;
    }

    /// <summary>One entry of the cover type list.</summary>
    private sealed class CoverTypeChoice
    {
        public CoverTypeChoice(BookCoverType coverType, string name)
        {
            CoverType = coverType;
            Name = name;
        }

        public BookCoverType CoverType { get; }

        public string Name { get; }

        public override string ToString() => Name;
    }

    /// <summary>One entry of a page list: a page the book records, in the order it prints.</summary>
    private sealed class PageItem
    {
        private PageItem(
            PageGroupRole role,
            string fileName,
            string name,
            string relativePath,
            string state)
        {
            Role = role;
            FileName = fileName;
            Name = name;
            RelativePath = relativePath;
            State = state;
            DesignVisibility = BookPages.FormatOf(role) == PageFormat.Rtf
                ? Visibility.Visible
                : Visibility.Collapsed;
        }

        public PageGroupRole Role { get; }

        /// <summary>Name of the page without its folder or extension, for example <c>title</c>.</summary>
        public string FileName { get; }

        /// <summary>Name of the page as the author sees it, for example <c>Title page</c>.</summary>
        public string Name { get; }

        /// <summary>File of the page relative to the book folder, as the configuration keeps it.</summary>
        public string RelativePath { get; }

        /// <summary>What the list says about the file of the page.</summary>
        public string State { get; }

        public Visibility DesignVisibility { get; }

        /// <summary>Whether the page has a page above it to trade places with.</summary>
        public bool UpEnabled { get; private set; }

        /// <summary>Whether the page has a page below it to trade places with.</summary>
        public bool DownEnabled { get; private set; }

        /// <summary>Offers the arrows of a page that has a page before it or after it to trade places with.</summary>
        public PageItem Movable(bool up, bool down)
        {
            UpEnabled = up;
            DownEnabled = down;

            return this;
        }

        public static PageItem Of(
            PageGroupRole role,
            string relativePath,
            string name,
            string state) =>
            new(
                role,
                BookPages.NameOfFile(relativePath),
                name,
                BookPages.Normalize(relativePath),
                state);

        public override string ToString() => Name;
    }
}
