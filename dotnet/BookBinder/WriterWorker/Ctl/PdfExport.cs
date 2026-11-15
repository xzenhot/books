using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using WriterWorker.Models;

namespace WriterWorker.Ctl;

/// <summary>Unit in which page sizes are entered and shown.</summary>
public enum PdfSizeUnit
{
    Millimetres,
    Inches
}

/// <summary>How the content of a book is spread over the pages of the PDF.</summary>
public enum PdfLayout
{
    /// <summary>The text flows from page to page as one continuous document.</summary>
    Continuous,

    /// <summary>
    /// Every chapter opens with its title alone on an odd page and every segment starts on a new
    /// page under its own title.
    /// </summary>
    ChapterPages
}

/// <summary>
/// Every page setup property of a PDF export in one place. The setup last used is kept in
/// <see cref="Current"/> and stored as JSON, so the next export - even in another session -
/// starts from the same paper, font, footer and background.
/// </summary>
public sealed class PdfExportOptions
{
    /// <summary>Page number pattern used when the caller does not choose one.</summary>
    public const string DefaultPageNumberFormat = "Page {page} of {total}";

    private const double MinimumMm = 25;
    private const double MaximumMm = 2000;
    private const double MaximumMarginMm = 100;
    private const double MinimumFontSize = 4;
    private const double MaximumFontSize = 96;

    private static readonly JsonSerializerOptions FileOptions = new()
    {
        WriteIndented = true,
        Converters = { new JsonStringEnumConverter() }
    };

    private static PdfExportOptions? _current;

    /// <summary>Width of the layout a book starts from: 8.5 inches, a letter sheet folded in half.</summary>
    public const double DefaultPageWidthMm = 215.9;

    /// <summary>Height of the layout a book starts from: 5.5 inches.</summary>
    public const double DefaultPageHeightMm = 139.7;

    /// <summary>Margin of the layout a book starts from: 20 mm.</summary>
    public const double DefaultMarginMm = 20;

    [JsonIgnore]
    public string? Title { get; set; }

    [JsonIgnore]
    public string? Author { get; set; }

    public double PageWidthMm { get; set; } = DefaultPageWidthMm;

    public double PageHeightMm { get; set; } = DefaultPageHeightMm;

    public double MarginMm { get; set; } = DefaultMarginMm;

    /// <summary>Unit the page size and the margin were entered in; sizes are stored in millimetres.</summary>
    public PdfSizeUnit SizeUnit { get; set; } = PdfSizeUnit.Inches;

    /// <summary>Family requested by the caller; auto-detected when null.</summary>
    public string? FontFamily { get; set; }

    /// <summary>Base font size in points; the document's own size is used when null.</summary>
    public double? FontSize { get; set; }

    /// <summary>Text printed in the footer of every page.</summary>
    public string? FooterText { get; set; }

    /// <summary>
    /// Page number pattern in which <c>{page}</c> and <c>{total}</c> are replaced, for example
    /// <c>"{page} / {total}"</c>. A book numbers the static pages that open it in roman numerals and
    /// its chapters from one, so <c>{page}</c> is a page number as printed rather than a page of the
    /// file. An empty value hides the page numbers; null uses
    /// <see cref="DefaultPageNumberFormat"/>.
    /// </summary>
    public string? PageNumberFormat { get; set; }

    /// <summary>
    /// Image drawn behind the text of every page. It is cropped around its middle to the shape of
    /// the page so that it covers the whole sheet.
    /// </summary>
    public string? BackgroundImagePath { get; set; }

    /// <summary>
    /// Image printed alone on the first page of a book export. The picture is stretched to the shape
    /// of the page, so it covers the sheet edge to edge with no margin and no white band.
    /// </summary>
    public string? FrontCoverImagePath { get; set; }

    /// <summary>
    /// Image printed alone on the last page of a book export. The picture is stretched to the shape
    /// of the page, so it covers the sheet edge to edge with no margin and no white band.
    /// </summary>
    public string? BackCoverImagePath { get; set; }

    /// <summary>
    /// Whether the cover images are added to a book export. A missing or unreadable file is skipped
    /// instead of failing the export.
    /// </summary>
    public bool IncludeCovers { get; set; } = true;

    /// <summary>
    /// Arrangement of a book export: one page per segment with chapter title pages, or the
    /// continuous flow of the reader. A plain rich text export always uses the continuous flow.
    /// </summary>
    public PdfLayout Layout { get; set; } = PdfLayout.ChapterPages;

    /// <summary>
    /// The setup shared by every export: read from disk on first use and then cached for the rest
    /// of the session. Callers that change it must work on a <see cref="Clone"/> and publish the
    /// result through <see cref="Remember"/>.
    /// </summary>
    public static PdfExportOptions Current => _current ??= Read();

    /// <summary>File holding the setup between sessions.</summary>
    public static string SettingsPath => AppStorage.PathFor(AppStorage.PdfSetupFileName);

    public PdfExportOptions Clone() => (PdfExportOptions)MemberwiseClone();

    /// <summary>Caches <paramref name="options"/> as <see cref="Current"/> and writes it to disk.</summary>
    public static void Remember(PdfExportOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);

        var cached = options.Clone();
        cached.Title = null;
        cached.Author = null;
        _current = cached;
        cached.Write();
    }

    private static PdfExportOptions Read()
    {
        PdfExportOptions? options = null;

        try
        {
            if (File.Exists(SettingsPath))
            {
                options = JsonSerializer.Deserialize<PdfExportOptions>(File.ReadAllText(SettingsPath), FileOptions);
            }
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or JsonException
            or NotSupportedException)
        {
            options = null;
        }

        options ??= new PdfExportOptions();
        options.Normalize();
        return options;
    }

    private void Write()
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath)!);
            File.WriteAllText(SettingsPath, JsonSerializer.Serialize(this, FileOptions));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or NotSupportedException)
        {
        }
    }

    /// <summary>Replaces values a hand-edited or outdated file may hold with usable defaults.</summary>
    internal void Normalize()
    {
        if (PageWidthMm is < MinimumMm or > MaximumMm)
        {
            PageWidthMm = DefaultPageWidthMm;
        }

        if (PageHeightMm is < MinimumMm or > MaximumMm)
        {
            PageHeightMm = DefaultPageHeightMm;
        }

        if (MarginMm is < 0 or > MaximumMarginMm)
        {
            MarginMm = DefaultMarginMm;
        }

        if (FontSize is < MinimumFontSize or > MaximumFontSize)
        {
            FontSize = null;
        }

        FontFamily = PdfFonts.FindFamily(FontFamily) ?? PdfExport.DefaultFontFamily;

        if (SizeUnit is not (PdfSizeUnit.Millimetres or PdfSizeUnit.Inches))
        {
            SizeUnit = PdfSizeUnit.Inches;
        }

        if (Layout is not (PdfLayout.Continuous or PdfLayout.ChapterPages))
        {
            Layout = PdfLayout.ChapterPages;
        }
    }
}

/// <summary>
/// Writes a <see cref="FlowDocument"/> - the content of a <see cref="RichTextBox"/> - to a PDF file.
/// The layout is produced by <see cref="QuestPdfExport"/>, whose Skia renderer shapes complex
/// scripts, so Bengali and other Indic books keep selectable, correctly ordered text.
/// </summary>
public static class PdfExport
{
    public const string PdfFileFilter = "PDF document (*.pdf)|*.pdf|All files (*.*)|*.*";

    internal const double DipToPoint = 72.0 / 96.0;

    /// <summary>
    /// Family preferred for every PDF export. AdorshoLipi is a Bengali-capable font, so a book in
    /// any supported script is rendered with a consistent face unless the caller asks for another.
    /// </summary>
    public static string DefaultFontFamily { get; set; } = "AdorshoLipi";

    /// <summary>
    /// Family used for the characters <see cref="DefaultFontFamily"/> cannot render. AdorshoLipi
    /// has no Latin letters, so digits, punctuation and Latin words are drawn with Kalpurush, which
    /// carries both scripts and keeps the page in a single Bengali font family.
    /// </summary>
    public static string AlternativeFontFamily { get; set; } = "Kalpurush";

    public static void Save(RichTextBox editor, string path, PdfExportOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(editor);
        Save(editor.Document, path, options);
    }

    public static void Save(FlowDocument document, string path, PdfExportOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(document);
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        QuestPdfExport.Save(document, path, options);
    }

    /// <summary>
    /// Exports a book straight from its chapters and segments: the static pages designed for the
    /// book first, then each chapter opened by a title page and each segment on its own page under
    /// its title. The front matter is numbered in roman numerals and the chapters from one. The
    /// renderer only needs the model, so a caller that already holds a <see cref="Book"/> skips the
    /// workspace read. Use the <see cref="FlowDocument"/> overload when the book should flow
    /// continuously instead.
    /// </summary>
    public static void Save(Book book, string path, PdfExportOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(book);
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        QuestPdfExport.Save(book, path, options);
    }

    internal static string PlainText(FlowDocument document)
        => new TextRange(document.ContentStart, document.ContentEnd).Text ?? string.Empty;

    /// <summary>
    /// Installed families a PDF export may use, in preference order: the requested family, then
    /// <see cref="DefaultFontFamily"/>, <see cref="AlternativeFontFamily"/>, the document's own font
    /// and finally the script fallbacks. The renderer walks the list per glyph, so a family without
    /// Latin letters still renders Latin text with the next family instead of dropping it.
    /// </summary>
    internal static IReadOnlyList<string> FontChain(FlowDocument document, string? requested)
        => FontChain(document.FontFamily?.Source, requested);

    /// <inheritdoc cref="FontChain(FlowDocument, string?)"/>
    internal static IReadOnlyList<string> FontChain(string? documentFamily, string? requested)
    {
        var chain = new List<string>();

        void Add(string? name)
        {
            var family = PdfFonts.FindFamily(name);
            if (family is not null && !chain.Contains(family, StringComparer.OrdinalIgnoreCase))
            {
                chain.Add(family);
            }
        }

        Add(requested);
        Add(DefaultFontFamily);
        Add(AlternativeFontFamily);
        Add(documentFamily);
        Add("Nirmala UI");
        Add("Kalpurush");
        Add("Siyam Rupali");
        Add("Nikosh");
        Add("SolaimanLipi");
        Add("Vrinda");
        Add("Segoe UI");
        Add("Arial");
        Add("Tahoma");
        Add("Times New Roman");
        Add(PdfFonts.FallbackFamily);

        return chain;
    }

    /// <summary>Colour a brush prints as on white paper.</summary>
    internal static Color ToPrintColor(Brush? brush)
    {
        if (brush is not SolidColorBrush solid)
        {
            return Colors.Black;
        }

        var color = solid.Color;
        if (color.A == 0)
        {
            return Colors.Black;
        }

        // Print on white paper: very light theme colours would be invisible.
        var luminance = (0.299 * color.R + 0.587 * color.G + 0.114 * color.B) / 255.0;
        return luminance > 0.75 ? Colors.Black : color;
    }
}
