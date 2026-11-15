using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using Microsoft.Win32;
using WriterWorker.Views;

namespace WriterWorker.Ctl;

/// <summary>
/// A rich text editor with a built-in command that exports its content to an RTF file.
/// </summary>
public partial class RichTextExportControl : UserControl
{
    public static readonly DependencyProperty DocumentNameProperty = DependencyProperty.Register(
        nameof(DocumentName),
        typeof(string),
        typeof(RichTextExportControl),
        new PropertyMetadata("Untitled", OnDocumentNameChanged));

    public RichTextExportControl()
    {
        InitializeComponent();
        Editor.Document.PagePadding = new Thickness(0);
        Editor.Document.PageWidth = double.NaN;
    }

    /// <summary>Raised after the document was written to disk.</summary>
    public event EventHandler<RtfExportedEventArgs>? Exported;

    /// <summary>Name shown in the toolbar and used as the default export file name.</summary>
    public string DocumentName
    {
        get => (string)GetValue(DocumentNameProperty);
        set => SetValue(DocumentNameProperty, value);
    }

    public FlowDocument Document => Editor.Document;

    public RichTextBox Editor => EditorBox;

    public string? LastExportPath { get; private set; }

    public void LoadRtf(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        RtfExport.Load(EditorBox, path);
        SetCurrentValue(DocumentNameProperty, Path.GetFileNameWithoutExtension(path));
        StatusText.Text = $"Loaded {path}";
    }

    public void SaveRtf(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        RtfExport.Save(EditorBox, path);
        LastExportPath = Path.GetFullPath(path);
        StatusText.Text = $"Exported to {LastExportPath}";
        Exported?.Invoke(this, new RtfExportedEventArgs(LastExportPath));
    }

    /// <summary>
    /// Shows a save dialog and exports the document. Returns <c>true</c> when a file was written.
    /// </summary>
    public bool ExportRtf()
    {
        var dialog = new SaveFileDialog
        {
            Title = "Export RTF",
            Filter = RtfExport.RtfFileFilter,
            DefaultExt = ".rtf",
            AddExtension = true,
            OverwritePrompt = true,
            FileName = GetSuggestedFileName()
        };

        if (!string.IsNullOrEmpty(LastExportPath))
            dialog.InitialDirectory = Path.GetDirectoryName(LastExportPath);

        if (dialog.ShowDialog(Window.GetWindow(this)) != true)
        {
            StatusText.Text = "Export cancelled";
            return false;
        }

        SaveRtf(dialog.FileName);
        return true;
    }

    /// <summary>
    /// Asks for the page setup, then shows a save dialog and exports the document as PDF.
    /// Returns <c>true</c> when a file was written.
    /// </summary>
    public bool ExportPdf(PdfExportOptions? options = null)
    {
        options ??= PdfExportOptions.Current.Clone();

        if (!PdfPageSetupDialog.TryAsk(Window.GetWindow(this), options, out options, showBookLayout: false))
        {
            StatusText.Text = "Export cancelled";
            return false;
        }

        var dialog = new SaveFileDialog
        {
            Title = "Export PDF",
            Filter = PdfExport.PdfFileFilter,
            DefaultExt = ".pdf",
            AddExtension = true,
            OverwritePrompt = true,
            FileName = Path.ChangeExtension(GetSuggestedFileName(), ".pdf")
        };

        if (!string.IsNullOrEmpty(LastExportPath))
            dialog.InitialDirectory = Path.GetDirectoryName(LastExportPath);

        if (dialog.ShowDialog(Window.GetWindow(this)) != true)
        {
            StatusText.Text = "Export cancelled";
            return false;
        }

        SavePdf(dialog.FileName, options);
        return true;
    }

    public void SavePdf(string path, PdfExportOptions? options = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        options ??= PdfExportOptions.Current.Clone();
        if (options.Title is null && !string.IsNullOrWhiteSpace(DocumentName))
        {
            options = options.Clone();
            options.Title = DocumentName;
        }

        PdfExport.Save(EditorBox, path, options);
        LastExportPath = Path.GetFullPath(path);
        StatusText.Text = $"Exported to {LastExportPath}";
        Exported?.Invoke(this, new RtfExportedEventArgs(LastExportPath));
    }

    private string GetSuggestedFileName()
    {
        var name = string.IsNullOrWhiteSpace(DocumentName) ? "Untitled" : DocumentName.Trim();
        foreach (var invalid in Path.GetInvalidFileNameChars())
            name = name.Replace(invalid, '_');

        return name + ".rtf";
    }

    private static void OnDocumentNameChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        var control = (RichTextExportControl)d;
        if (control.StatusText is not null && string.IsNullOrEmpty(control.LastExportPath))
            control.StatusText.Text = "Ready";
    }

    private void OnExportClick(object sender, RoutedEventArgs e)
    {
        try
        {
            ExportRtf();
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or ArgumentException)
        {
            StatusText.Text = "Export failed";
            MessageBox.Show(
                Window.GetWindow(this),
                $"The document could not be exported.\n\n{ex.Message}",
                "Export RTF",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    private void OnExportPdfClick(object sender, RoutedEventArgs e)
    {
        try
        {
            ExportPdf();
        }
        catch (Exception ex) when (ex is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException
            or InvalidOperationException)
        {
            StatusText.Text = "Export failed";
            MessageBox.Show(
                Window.GetWindow(this),
                $"The document could not be exported to PDF.\n\n{ex.Message}",
                "Export PDF",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
    }

    private void OnEditorPreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.S && Keyboard.Modifiers == ModifierKeys.Control)
        {
            OnExportClick(sender, e);
            e.Handled = true;
        }
    }
}
