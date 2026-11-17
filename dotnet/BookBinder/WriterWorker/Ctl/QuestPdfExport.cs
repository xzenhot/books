using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;
using WriterWorker.Configuration;
using WriterWorker.Models;
using WriterWorker.Views;
using QColor = QuestPDF.Infrastructure.Color;
using QFontWeight = QuestPDF.Infrastructure.FontWeight;
using QPageSize = QuestPDF.Helpers.PageSize;
using QSettings = QuestPDF.Settings;
using QTextStyle = QuestPDF.Infrastructure.TextStyle;
using QUnit = QuestPDF.Infrastructure.Unit;

namespace WriterWorker.Ctl;

/// <summary>
/// Writes a <see cref="FlowDocument"/> to PDF through QuestPDF, which lays the document out with
/// its own engine and renders it with Skia. Skia shapes complex scripts, so Bengali, Devanagari,
/// Arabic and similar books keep their text selectable and still look correct.
/// <para>
/// QuestPDF requires a license to be selected before it generates a document. The free
/// <see cref="LicenseType.Community"/> license applies to individuals and companies below the
/// revenue threshold of QuestPDF's terms; set <see cref="License"/> to another value if that does
/// not fit your use.
/// </para>
/// </summary>
public static class QuestPdfExport
{
    private const double DipToPoint = PdfExport.DipToPoint;

    /// <summary>Chapter titles print at twice the body size, segment titles at one and a half.</summary>
    private const double ChapterTitleScale = 2.0;
    private const double SegmentTitleScale = 1.5;

    /// <summary>Height of one line of body text relative to the font size, in points.</summary>
    private const double BodyLineHeight = 1.2;

    /// <summary>Pages kept for the index the export builds from the contents of the book.</summary>
    private const int IndexPageCount = 2;

    /// <summary>
    /// Names of the two numbered parts of a book: the front matter of static pages, numbered in
    /// roman numerals, and the body of chapters, numbered from one in arabic ones.
    /// </summary>
    private const string FrontMatterSection = "front-matter";

    private const string BodySection = "body";

    /// <summary>
    /// Roman numerals up to four thousand, largest first, for numbering the front matter of a book.
    /// </summary>
    private static readonly (int Value, string Symbol)[] RomanNumerals =
    {
        (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"),
        (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
        (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")
    };

    private static readonly QColor FooterColor = QColor.FromRGB(130, 130, 130);

    /// <summary>Background images cropped to a page shape, keyed by their file, shared by every export.</summary>
    private static readonly Dictionary<string, (long Stamp, double Aspect, byte[]? Bytes)> ImageCache =
        new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Cover images already resampled to the shape of a page, keyed by file and page size.</summary>
    private static readonly Dictionary<string, (long Stamp, byte[] Bytes)> CoverCache =
        new(StringComparer.OrdinalIgnoreCase);

    private static bool _settingsApplied;

    /// <summary>License reported to QuestPDF; defaults to the free community license.</summary>
    public static LicenseType License { get; set; } = LicenseType.Community;

    public static void Save(FlowDocument document, string path, PdfExportOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(document);
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        Write(CreateDocument(document, options), path);
    }

    /// <summary>
    /// Exports a book from its segments: every segment starts on a new page under its title, and
    /// every chapter opens with a title page that is kept on an odd page.
    /// </summary>
    public static void Save(Book book, string path, PdfExportOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(book);
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        Write(CreateDocument(book, options), path);
    }

    private static void Write(QuestPDF.Fluent.Document document, string path)
    {
        var fullPath = Path.GetFullPath(path);
        var directory = Path.GetDirectoryName(fullPath);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        ApplySettings();

        document.GeneratePdf(fullPath);
    }

    /// <summary>
    /// Builds the QuestPDF document without writing it, so callers can preview pages or merge it
    /// into another PDF.
    /// </summary>
    public static QuestPDF.Fluent.Document CreateDocument(FlowDocument document, PdfExportOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(document);

        options ??= PdfExportOptions.Current.Clone();
        ApplySettings();

        return Build(document, options);
    }

    /// <summary>Builds the segment based book layout without writing it.</summary>
    public static QuestPDF.Fluent.Document CreateDocument(Book book, PdfExportOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(book);

        options ??= PdfExportOptions.Current.Clone();
        ApplySettings();

        return BuildBook(book, options);
    }

    private static void ApplySettings()
    {
        QSettings.License = License;

        if (_settingsApplied)
        {
            return;
        }

        QSettings.UseSystemFonts = true;
        // Missing families or glyphs fall back to the next family instead of failing the export.
        QSettings.ThrowOnMissingFontFamilies = false;
        QSettings.ThrowOnMissingTextGlyphs = false;

        _settingsApplied = true;
    }

    private static QuestPDF.Fluent.Document Build(FlowDocument source, PdfExportOptions options)
    {
        var documentSize = source.FontSize > 0 && !double.IsNaN(source.FontSize) ? source.FontSize * DipToPoint : 0;
        var setup = CreateSetup(options, PdfExport.FontChain(source, options.FontFamily).ToArray(), documentSize);

        return QuestPDF.Fluent.Document.Create(container =>
            {
                container.Page(page => ComposePage(page, setup, column =>
                {
                    var writer = new BlockWriter(
                        column,
                        setup.Families,
                        setup.BaseSize,
                        documentSize,
                        PdfFonts.FindFamily(source.FontFamily?.Source));

                    foreach (var block in source.Blocks)
                    {
                        writer.AddBlock(block, 0);
                    }
                }));
            })
            .WithMetadata(Metadata(options));
    }

    /// <summary>
    /// Lays the book out the way its <c>pages</c> section orders it: the page folders print in the
    /// order the configuration records, and each folder prints the pages it lists in the order they
    /// print - the cover images edge to edge, the designed pages, the pages kept for the index, the
    /// chapters with their segment pages and the appendix. Everything printed before the content is
    /// numbered in roman numerals, and everything from the content on in arabic ones, so every
    /// chapter still opens on an odd printed page whatever the front matter holds.
    /// </summary>
    private static QuestPDF.Fluent.Document BuildBook(Book book, PdfExportOptions options)
    {
        // A profile keeps the covers and the background relative to the book folder, so the source of
        // the book stays portable; the export needs them as files on disk.
        options = BookProfile.ResolvedPaths(book.FolderPath, options);

        var chapters = book.Chapters.Where(HasContent).ToList();
        var documentSize = MarkdownFlow.DefaultFontSize * DipToPoint;
        var setup = CreateSetup(
            options,
            PdfExport.FontChain(MarkdownFlow.DefaultFontFamily, options.FontFamily).ToArray(),
            documentSize);

        // The two parts of the book are numbered apart: everything before the content is front
        // matter and counts in roman numerals, the content starts the body, which counts from one in
        // arabic ones, and the appendix goes on counting with the chapters.
        var frontSetup = setup with { NumberSection = FrontMatterSection, NumberFormatter = RomanNumber };
        var body = setup with { NumberSection = BodySection };
        var plan = PlanChapterStarts(chapters, body, documentSize);
        var groups = BookGroups(book.FolderPath);
        var contentOrder = groups.FirstOrDefault(group => group.Role == PageGroupRole.Content)?.Order ?? int.MaxValue;

        return QuestPDF.Fluent.Document.Create(container =>
            {
                var printed = 0;
                var closing = new List<byte[]?>();

                // Every page of a numbered part carries the name of that part, because a section is
                // counted over the pages that name it: the front matter counts in roman numerals and
                // the body from the content on in arabic ones, so a footer reads "page iii of ix" and
                // then "page 1 of 158" instead of counting the page it sits on.
                void Compose(PageSetup partSetup, Action<ColumnDescriptor> content)
                {
                    container.Page(page => ComposePage(
                        page,
                        partSetup,
                        content,
                        partSetup.NumberSection));

                    printed++;
                }

                void PrintCover(byte[]? image)
                {
                    container.Page(page =>
                    {
                        if (image is null)
                        {
                            ComposeBlankPage(page, setup);
                        }
                        else
                        {
                            ComposeCoverPage(page, setup, image);
                        }
                    });

                    printed++;
                }

                void PrintChapters(PageSetup partSetup) =>
                    Compose(partSetup, column => WriteChapters(column, chapters, plan, partSetup, documentSize));

                // A blank page is recorded like any other page of its part but has no design, so it
                // prints as a sheet of its own, where the part prints it.
                void PrintBlanks(BookPageGroup group, PageSetup partSetup)
                {
                    var count = group.Printed.Count(BookPages.IsBlank);

                    if (count > 0)
                    {
                        Compose(partSetup, column => WriteReservedPages(column, count));
                    }
                }

                if (groups.Count == 0)
                {
                    // A book outside a workspace has no page folders, so the covers of the export and
                    // the chapters still print the way they always did.
                    if (CoverImage(options, options.FrontCoverImagePath, book.FolderPath) is { } front)
                    {
                        PrintCover(front);
                    }

                    if (chapters.Count > 0)
                    {
                        PrintChapters(body);
                    }

                    if (CoverImage(options, options.BackCoverImagePath, book.FolderPath) is { } back)
                    {
                        PrintCover(back);
                    }
                }
                else
                {
                    // A book whose page folders hold no cover image still prints the covers the
                    // setup dialog picked, so browsing for a cover is not lost to an empty folder.
                    var fromPages = groups
                        .FirstOrDefault(group => group.Role == PageGroupRole.Cover)
                        ?.Printed.Any() == true;

                    if (!fromPages && CoverImage(options, options.FrontCoverImagePath, book.FolderPath) is { } fallbackFront)
                    {
                        PrintCover(fallbackFront);
                    }

                    foreach (var group in groups)
                    {
                        var inBody = group.Role is PageGroupRole.Content or PageGroupRole.Appendix
                            || group.Order > contentOrder;
                        var partSetup = inBody ? body : frontSetup;

                        switch (group.Role)
                        {
                            case PageGroupRole.Cover:
                                foreach (var file in group.Printed)
                                {
                                    if (BookPages.IsBlank(file))
                                    {
                                        // A blank page of the cover folder prints as a sheet of its
                                        // own, the way the covers print: no margin and no footer.
                                        PrintCover(null);
                                        continue;
                                    }

                                    if (BookPages.FormatOf(file, group.Format) != PageFormat.Image
                                        || CoverImage(options, BookPages.Resolve(ProfileBase(book.FolderPath), file.FilePath)) is not { } image)
                                    {
                                        continue;
                                    }

                                    // The back cover closes the book whatever position its folder
                                    // records for it, because a printed book ends with the cover it
                                    // began with.
                                    if (string.Equals(file.Name, "back", StringComparison.OrdinalIgnoreCase))
                                    {
                                        closing.Add(image);
                                        continue;
                                    }

                                    PrintCover(image);
                                }

                                break;

                            case PageGroupRole.Content:
                                if (chapters.Count > 0)
                                {
                                    PrintChapters(body);
                                }

                                // The body is printed from the chapters, so a blank page kept in the
                                // content folder prints after them, at the end of the body.
                                PrintBlanks(group, body);
                                break;

                            case PageGroupRole.BackCover:
                                // The back cover closes the book, so its pages are kept back and
                                // printed after every other page whatever order the folder records.
                                foreach (var file in group.Printed)
                                {
                                    if (BookPages.IsBlank(file))
                                    {
                                        closing.Add(null);
                                    }
                                    else if (BookPages.FormatOf(file, group.Format) == PageFormat.Image
                                        && CoverImage(options, BookPages.Resolve(ProfileBase(book.FolderPath), file.FilePath)) is { } image)
                                    {
                                        closing.Add(image);
                                    }
                                }

                                break;

                            case PageGroupRole.Index:
                                // The index is written from the chapters of the book by the setup
                                // window, so the pages of the folder are printed where they are. A
                                // book whose index was never built prints the pages the export
                                // reserves for it, and the empty sheets kept after them.
                                if (Designs(book.FolderPath, group) is { Count: > 0 } index)
                                {
                                    Compose(partSetup, column => WriteDesigns(column, index, partSetup, documentSize));
                                }
                                else
                                {
                                    Compose(partSetup, column => WriteReservedPages(column, IndexPageCount));
                                }

                                PrintBlanks(group, partSetup);
                                break;

                            default:
                                if (Designs(book.FolderPath, group) is { Count: > 0 } designs)
                                {
                                    Compose(partSetup, column => WriteDesigns(column, designs, partSetup, documentSize));
                                }

                                break;
                        }
                    }

                    foreach (var image in closing)
                    {
                        PrintCover(image);
                    }

                    if (closing.Count == 0 && !fromPages
                        && CoverImage(options, options.BackCoverImagePath, book.FolderPath) is { } fallbackBack)
                    {
                        PrintCover(fallbackBack);
                    }

                    if (printed == 0)
                    {
                        // A book with nothing to print still needs a sheet to be a document.
                        Compose(frontSetup, column => column.Item().Text(" "));
                    }
                }
            })
            .WithMetadata(Metadata(options));
    }

    /// <summary>
    /// Folder a page path of a profile is recorded against: the folder the profile sits in, so
    /// <c>pages/cover/front.jpg</c> names a file of the profile and not of the workspace.
    /// </summary>
    private static string? ProfileBase(string? bookFolder) =>
        string.IsNullOrWhiteSpace(bookFolder) ? null : BookProfile.ProfileFolderOf(bookFolder);

    /// <summary>
    /// The page folders of <paramref name="bookFolder"/> in print order. The folders the book does
    /// not have yet are added and the pages every book prints - the title page and the publisher
    /// page - are written with starter content, because a book that has never been set up must still
    /// print its front matter. A folder that cannot be written to is read as it is rather than
    /// failing the export.
    /// </summary>
    private static IReadOnlyList<BookPageGroup> BookGroups(string? bookFolder)
    {
        if (string.IsNullOrWhiteSpace(bookFolder))
        {
            return [];
        }

        try
        {
            return PageStore.Ensure(bookFolder, BookLayout.LoadBook(bookFolder));
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or ArgumentException
            or NotSupportedException)
        {
            return PageStore.Load(bookFolder);
        }
    }

    /// <summary>
    /// The pages of <paramref name="group"/> in the order they print, read from their RTF files. A
    /// page whose file is missing or cannot be read is left out, so a broken design never fails an
    /// export. A dedication is followed by a blank page, so the page after it opens on the right-hand
    /// side of a spread, and a page kept blank prints blank: a null entry is a page that prints blank.
    /// </summary>
    private static List<FlowDocument?> Designs(string? bookFolder, BookPageGroup group)
    {
        var designs = new List<FlowDocument?>();

        foreach (var file in group.Printed)
        {
            // A blank page is kept to fill a sheet, so it prints as one whether or not a design was
            // ever written for it.
            if (BookPages.IsBlank(file))
            {
                designs.Add(null);
                continue;
            }

            if (BookPages.FormatOf(file, group.Format) != PageFormat.Rtf
                || BookPages.Resolve(ProfileBase(bookFolder), file.FilePath) is not { } path
                || !File.Exists(path))
            {
                continue;
            }

            try
            {
                designs.Add(RtfExport.LoadDocument(path));
            }
            catch (Exception exception) when (exception is not OutOfMemoryException)
            {
                // A page that cannot be read is skipped; the rest of the book still prints.
                continue;
            }

            if (file.Name is "dedicate" or "dedication")
            {
                designs.Add(null);
            }
        }

        return designs;
    }

    /// <summary>
    /// Prints the chapters of the book: each one opens with its title alone on an odd page, and each
    /// segment starts a page of its own under its title.
    /// </summary>
    private static void WriteChapters(
        ColumnDescriptor column,
        IReadOnlyList<Chapter> chapters,
        BookPlan plan,
        PageSetup setup,
        double documentSize)
    {
        for (var index = 0; index < chapters.Count; index++)
        {
            if (index > 0)
            {
                column.Item().PageBreak();
            }

            if (plan.BlankBefore[index])
            {
                // The filler page moves the chapter title onto the next odd page.
                column.Item().Text(" ");
                column.Item().PageBreak();
            }

            WriteChapterTitle(column, chapters[index], setup);
            column.Item().PageBreak();
            WriteChapterBody(column, chapters[index], setup, documentSize);
        }
    }

    /// <summary>
    /// Prints <paramref name="count"/> pages kept for a page the export fills in later. An empty
    /// paragraph gives each reserved page a body of its own; a bare page break would leave the page
    /// out altogether.
    /// </summary>
    private static void WriteReservedPages(ColumnDescriptor column, int count)
    {
        for (var index = 0; index < count; index++)
        {
            if (index > 0)
            {
                column.Item().PageBreak();
            }

            column.Item().Text(" ");
        }
    }

    /// <summary>
    /// Prints the designed pages, each one starting on a new page. The caller wraps them in the
    /// section of the book they belong to, so the footer numbers them with the rest of that part. A
    /// null entry is a page that prints blank, kept for a page the export fills in later.
    /// </summary>
    private static void WriteDesigns(
        ColumnDescriptor column,
        IReadOnlyList<FlowDocument?> designs,
        PageSetup setup,
        double documentSize)
    {
        for (var index = 0; index < designs.Count; index++)
        {
            if (index > 0)
            {
                column.Item().PageBreak();
            }

            if (designs[index] is not { } design)
            {
                // An empty paragraph gives the reserved page a body of its own; a bare page break
                // would leave the page out altogether.
                column.Item().Text(" ");
                continue;
            }

            var writer = new BlockWriter(
                column,
                setup.Families,
                setup.BaseSize,
                documentSize,
                PdfFonts.FindFamily(design.FontFamily?.Source));

            foreach (var block in design.Blocks)
            {
                writer.AddBlock(block, 0);
            }
        }
    }

    /// <summary>
    /// A cover image resampled to the exact shape of the page it is printed on, or null when the
    /// covers are switched off or the file is gone - a missing cover never fails the export. The
    /// picture is stretched to the page shape here, once, so that printing it can only fill the
    /// sheet: no band is left at any edge and the margins play no part. A path kept relative to
    /// the profile folder of <paramref name="bookFolder"/> - which is how the profile of a book
    /// records its covers, so the source stays portable - is resolved against it.
    /// </summary>
    private static byte[]? CoverImage(PdfExportOptions options, string? path, string? bookFolder = null)
    {
        if (!options.IncludeCovers)
        {
            return null;
        }

        return PageShapedImage(
            BookPages.Resolve(ProfileBase(bookFolder), path) ?? path,
            options.PageWidthMm,
            options.PageHeightMm);
    }

    /// <summary>
    /// Bytes of an image resampled so that its pixels are exactly the shape of a page of
    /// <paramref name="widthMm"/> by <paramref name="heightMm"/>, or null when the file is gone.
    /// Every pixel of the picture is kept and stretched over the whole page, so the result fills the
    /// sheet edge to edge however the source was shaped.
    /// </summary>
    private static byte[]? PageShapedImage(string? path, double widthMm, double heightMm)
    {
        var full = ExistingFile(path);
        if (full is null || widthMm <= 0 || heightMm <= 0)
        {
            return null;
        }

        var key = $"{full}|{widthMm:F2}x{heightMm:F2}";
        var stamp = File.GetLastWriteTimeUtc(full).Ticks;
        lock (ImageCache)
        {
            if (CoverCache.TryGetValue(key, out var cached) && cached.Stamp == stamp)
            {
                return cached.Bytes;
            }
        }

        byte[] bytes;
        try
        {
            bytes = StretchToPage(File.ReadAllBytes(full), widthMm, heightMm);
        }
        catch (Exception exception) when (exception is IOException
            or UnauthorizedAccessException
            or NotSupportedException
            or ArgumentException
            or InvalidOperationException
            or OutOfMemoryException)
        {
            return null;
        }

        lock (ImageCache)
        {
            if (CoverCache.Count > 8)
            {
                CoverCache.Clear();
            }

            CoverCache[key] = (stamp, bytes);
        }

        return bytes;
    }

    /// <summary>
    /// Resamples an encoded image onto a canvas of exactly the page shape. The pixel count is kept
    /// close to the source, so the cover neither loses detail nor grows, while the aspect ratio is
    /// that of the page: drawn over the page it fills it with nothing left over.
    /// </summary>
    private static byte[] StretchToPage(byte[] source, double widthMm, double heightMm)
    {
        BitmapSource bitmap;
        using (var stream = new MemoryStream(source))
        {
            bitmap = BitmapFrame.Create(stream, BitmapCreateOptions.None, BitmapCacheOption.OnLoad);
        }

        var pageAspect = widthMm / heightMm;
        var area = Math.Max(1.0, (double)bitmap.PixelWidth * bitmap.PixelHeight);
        var targetWidth = (int)Math.Round(Math.Sqrt(area * pageAspect));
        var targetHeight = (int)Math.Round(targetWidth / pageAspect);

        // Keep a very large source from turning into an unmanageable bitmap; the PDF scales it back
        // down to the page anyway.
        const int LongestSide = 4000;
        var longest = Math.Max(targetWidth, targetHeight);
        if (longest > LongestSide)
        {
            var shrink = (double)LongestSide / longest;
            targetWidth = Math.Max(1, (int)Math.Round(targetWidth * shrink));
            targetHeight = Math.Max(1, (int)Math.Round(targetHeight * shrink));
        }

        targetWidth = Math.Max(1, targetWidth);
        targetHeight = Math.Max(1, targetHeight);

        var visual = new DrawingVisual();
        RenderOptions.SetBitmapScalingMode(visual, BitmapScalingMode.HighQuality);
        using (var context = visual.RenderOpen())
        {
            // Filling the whole canvas is what stretches the picture to the page shape.
            context.DrawImage(bitmap, new Rect(0, 0, targetWidth, targetHeight));
        }

        var canvas = new RenderTargetBitmap(targetWidth, targetHeight, 96, 96, PixelFormats.Pbgra32);
        canvas.Render(visual);
        canvas.Freeze();
        return Encode(canvas);
    }

    /// <summary>
    /// Prints a cover on the whole sheet: no margin, no background image and no footer. The image
    /// was already resampled to the shape of the page, so it is stretched over the sheet and covers
    /// every millimetre of it.
    /// </summary>
    private static void ComposeCoverPage(PageDescriptor page, PageSetup setup, byte[] cover)
    {
        page.Size(setup.Size);
        page.Margin(0, QUnit.Millimetre);
        page.PageColor(QColor.FromRGB(255, 255, 255));
        page.Content().Image(cover).FitUnproportionally();
    }

    /// <summary>
    /// Prints a sheet with nothing on it, where a cover prints: no margin, no footer and no number,
    /// so a blank page of the cover or of the back cover reads as an empty sheet of the book.
    /// </summary>
    private static void ComposeBlankPage(PageDescriptor page, PageSetup setup)
    {
        page.Size(setup.Size);
        page.Margin(0, QUnit.Millimetre);
        page.PageColor(QColor.FromRGB(255, 255, 255));
        page.Content().Text(" ");
    }

    /// <summary>The full path of an image that is actually on disk, or null when it is not.</summary>
    private static string? ExistingFile(string? path)
    {
        var trimmed = path?.Trim();
        if (string.IsNullOrEmpty(trimmed))
        {
            return null;
        }

        string full;
        try
        {
            full = Path.GetFullPath(trimmed);
        }
        catch (ArgumentException)
        {
            return null;
        }
        catch (NotSupportedException)
        {
            return null;
        }

        return File.Exists(full) ? full : null;
    }

    /// <summary>
    /// Bytes of an image cropped around its middle so that its proportions match a page of
    /// <paramref name="widthMm"/> by <paramref name="heightMm"/>. QuestPDF cannot clip an image, so
    /// a background that does not share the page shape would be letterboxed with white bands;
    /// cropping here is what makes it cover the sheet edge to edge. Returns null when the file is
    /// missing or unreadable. Results are cached, as a book is laid out twice.
    /// </summary>
    private static byte[]? FullBleedImage(string? path, double widthMm, double heightMm)
    {
        if (widthMm <= 0 || heightMm <= 0)
        {
            return null;
        }

        var full = ExistingFile(path);
        if (full is null)
        {
            return null;
        }

        var aspect = widthMm / heightMm;
        var stamp = File.GetLastWriteTimeUtc(full).Ticks;

        lock (ImageCache)
        {
            if (ImageCache.TryGetValue(full, out var cached)
                && cached.Stamp == stamp
                && cached.Aspect.Equals(aspect))
            {
                return cached.Bytes;
            }
        }

        byte[]? bytes;
        try
        {
            bytes = CropToAspect(full, aspect);
        }
        catch (Exception exception) when (exception is IOException
            or NotSupportedException
            or ArgumentException
            or InvalidOperationException
            or OutOfMemoryException)
        {
            return null;
        }

        lock (ImageCache)
        {
            if (ImageCache.Count > 16)
            {
                ImageCache.Clear();
            }

            ImageCache[full] = (stamp, aspect, bytes);
        }

        return bytes;
    }

    private static byte[] CropToAspect(string path, double aspect)
    {
        using var source = File.OpenRead(path);
        var decoder = BitmapDecoder.Create(
            source,
            BitmapCreateOptions.PreservePixelFormat,
            BitmapCacheOption.OnLoad);
        var frame = decoder.Frames[0];
        var width = frame.PixelWidth;
        var height = frame.PixelHeight;
        var sourceAspect = (double)width / height;

        if (Math.Abs(sourceAspect - aspect) <= 0.002)
        {
            // Already the shape of the page: hand the file over untouched so a JPEG is not
            // re-encoded into a much larger lossless image.
            source.Position = 0;
            using var untouched = new MemoryStream();
            source.CopyTo(untouched);
            return untouched.ToArray();
        }

        var cropWidth = width;
        var cropHeight = height;
        if (sourceAspect > aspect)
        {
            cropWidth = Math.Max(1, (int)Math.Round(height * aspect));
        }
        else
        {
            cropHeight = Math.Max(1, (int)Math.Round(width / aspect));
        }

        var cropped = new CroppedBitmap(
            frame,
            new Int32Rect((width - cropWidth) / 2, (height - cropHeight) / 2, cropWidth, cropHeight));

        return Encode(cropped);
    }

    /// <summary>
    /// Encodes the cropped image, keeping whichever of the two encodings is smaller: a background
    /// that is mostly flat colour with lettering stays lossless, while a photograph is stored as a
    /// JPEG so that the PDF does not grow by megabytes. An image with transparency keeps its PNG,
    /// as a JPEG would paint the transparent parts black.
    /// </summary>
    private static byte[] Encode(BitmapSource image)
    {
        var png = Encode(image, new PngBitmapEncoder());
        if (image.Format.Masks.Count > 3)
        {
            return png;
        }

        // A JPEG cannot hold every pixel format a decoder or a bitmap may report, so the crop is
        // converted to plain 24 bit colour first.
        var jpeg = Encode(new FormatConvertedBitmap(image, PixelFormats.Bgr24, null, 0), new JpegBitmapEncoder { QualityLevel = 92 });
        return jpeg.Length < png.Length ? jpeg : png;
    }

    private static byte[] Encode(BitmapSource image, BitmapEncoder encoder)
    {
        encoder.Frames.Add(BitmapFrame.Create(image));
        using var output = new MemoryStream();
        encoder.Save(output);
        return output.ToArray();
    }

    /// <summary>
    /// Works out which chapters need a filler page in front of them so that every chapter title
    /// lands on an odd page of the body. QuestPDF cannot report the page a block lands on, so every
    /// chapter body is laid out once on its own to learn how many pages it takes; the same page
    /// template and footer guarantee the final document paginates the body the same way.
    /// </summary>
    private static BookPlan PlanChapterStarts(List<Chapter> chapters, PageSetup setup, double documentSize)
    {
        var blankBefore = new bool[chapters.Count];
        var pages = 0;

        for (var index = 0; index < chapters.Count; index++)
        {
            blankBefore[index] = (pages + 1) % 2 == 0;

            if (blankBefore[index])
            {
                pages++;
            }

            pages++;

            pages += CountBodyPages(chapters[index], setup, documentSize);
        }

        return new BookPlan(blankBefore);
    }

    private static int CountBodyPages(Chapter chapter, PageSetup setup, double documentSize)
    {
        // The probe starts on page one of its own document and needs no numbering of its own, only
        // the same text area, so the page number is not looked up in a section that is not there.
        var probeSetup = setup with { NumberSection = null, NumberFormatter = null };

        var probe = QuestPDF.Fluent.Document.Create(container =>
            container.Page(page => ComposePage(
                page,
                probeSetup,
                column => WriteChapterBody(column, chapter, probeSetup, documentSize))));

        return CountPages(probe);
    }

    /// <summary>
    /// Pages a document is laid out on. The SVG backend paginates without rasterising the pages,
    /// which keeps the probe cheap; the image backend is the fallback when it is unavailable.
    /// </summary>
    private static int CountPages(QuestPDF.Fluent.Document document)
    {
        try
        {
            var count = document.GenerateSvg().Count;
            if (count > 0)
            {
                return count;
            }
        }
        catch (Exception exception) when (exception is not OutOfMemoryException)
        {
            // Fall back to counting rendered pages.
        }

        return document.GenerateImages(new ImageGenerationSettings { RasterDpi = 20 }).Count();
    }

    private static void WriteChapterTitle(ColumnDescriptor column, Chapter chapter, PageSetup setup)
    {
        // The title sits alone on its page, about a third of the way down the text area.
        var top = setup.ContentHeightMm * 0.3;

        column.Item()
            .PaddingTop((float)top, QUnit.Millimetre)
            .Text(text =>
            {
                text.AlignCenter();
                text.DefaultTextStyle(style => style
                    .FontFamily(setup.Families)
                    .FontSize((float)(setup.BaseSize * ChapterTitleScale))
                    .Weight(QFontWeight.SemiBold));
                text.Span(ChapterTitle(chapter));
            });
    }

    private static void WriteChapterBody(
        ColumnDescriptor column,
        Chapter chapter,
        PageSetup setup,
        double documentSize)
    {
        var parts = new List<(string? Title, string Text)>();

        foreach (var segment in chapter.Segments)
        {
            var text = segment.Body;
            if (!string.IsNullOrWhiteSpace(text))
            {
                parts.Add((SegmentTitle(segment), text));
            }
        }

        if (parts.Count == 0 && !string.IsNullOrWhiteSpace(chapter.Body))
        {
            parts.Add((null, chapter.Body!));
        }

        for (var index = 0; index < parts.Count; index++)
        {
            if (index > 0)
            {
                column.Item().PageBreak();
            }

            if (parts[index].Title is { } title)
            {
                WriteSegmentTitle(column, title, setup);
            }

            var source = MarkdownFlow.Build(parts[index].Text);
            var writer = new BlockWriter(
                column,
                setup.Families,
                setup.BaseSize,
                documentSize,
                PdfFonts.FindFamily(source.FontFamily?.Source));

            foreach (var block in source.Blocks)
            {
                writer.AddBlock(block, 0);
            }
        }
    }

    private static void WriteSegmentTitle(ColumnDescriptor column, string title, PageSetup setup)
    {
        // A blank line of body text keeps the title off the first paragraph of the segment.
        column.Item()
            .PaddingBottom((float)(setup.BaseSize * BodyLineHeight))
            .Text(text =>
            {
                text.DefaultTextStyle(style => style
                    .FontFamily(setup.Families)
                    .FontSize((float)(setup.BaseSize * SegmentTitleScale))
                    .Weight(QFontWeight.SemiBold));
                text.Span(title);
            });
    }

    private static bool HasContent(Chapter chapter)
        => chapter.Segments.Any(segment => !string.IsNullOrWhiteSpace(segment.Body))
            || !string.IsNullOrWhiteSpace(chapter.Body);

    private static string ChapterTitle(Chapter chapter)
        => FirstText(chapter.Title, chapter.Name, $"Chapter {chapter.Index}");

    private static string? SegmentTitle(Segment segment)
        => FirstText(segment.Title) is { Length: > 0 } title
            ? title
            : segment.Index > 0 ? $"Segment {segment.Index}" : null;

    private static string FirstText(params string?[] values)
        => values.Select(value => value?.Trim()).FirstOrDefault(value => !string.IsNullOrEmpty(value)) ?? string.Empty;

    private static PageSetup CreateSetup(
        PdfExportOptions options,
        string[] families,
        double documentSize)
    {
        var background = FullBleedImage(
            options.BackgroundImagePath,
            options.PageWidthMm,
            options.PageHeightMm);

        var footer = options.FooterText?.Trim();

        return new PageSetup(
            new QPageSize(MmToPoints(options.PageWidthMm), MmToPoints(options.PageHeightMm), QUnit.Point),
            (float)options.MarginMm,
            options.PageWidthMm,
            options.PageHeightMm,
            families,
            options.FontSize is > 0 ? options.FontSize.Value : documentSize > 0 ? documentSize : 12.0,
            string.IsNullOrEmpty(footer) ? null : footer,
            NormalizeNumberFormat(options.PageNumberFormat),
            background);
    }

    private static void ComposePage(
        PageDescriptor page,
        PageSetup setup,
        Action<ColumnDescriptor> content,
        string? section = null)
    {
        page.Size(setup.Size);
        page.Margin(setup.MarginMm, QUnit.Millimetre);
        page.PageColor(QColor.FromRGB(255, 255, 255));

        if (setup.Background is not null)
        {
            // Already cropped to the page shape, so stretching it cannot distort it and leaves no
            // uncovered edge.
            page.Background().Image(setup.Background).FitUnproportionally();
        }

        page.DefaultTextStyle(style => style
            .FontFamily(setup.Families)
            .FontSize((float)setup.BaseSize)
            .FontColor(QColor.FromRGB(0, 0, 0)));

        // The section names the part of the book the page is numbered in, so it has to be taken by
        // the page content itself rather than by an item inside it.
        var contentContainer = page.Content();
        if (section is not null)
        {
            contentContainer = contentContainer.Section(section);
        }

        contentContainer.Column(column =>
        {
            column.Spacing(0, QUnit.Point);
            content(column);
        });

        WriteFooter(page, setup);
    }

    private static void WriteFooter(PageDescriptor page, PageSetup setup)
    {
        var footerText = setup.FooterText;
        var numberFormat = setup.NumberFormat;

        if (footerText is null && numberFormat is null)
        {
            return;
        }

        if (footerText is not null && numberFormat is not null)
        {
            Footer(page, setup).Row(row =>
            {
                row.RelativeItem().AlignLeft().Text(text =>
                {
                    text.DefaultTextStyle(FooterStyle);
                    text.Span(footerText);
                });

                row.RelativeItem().AlignRight().Text(text =>
                {
                    text.DefaultTextStyle(FooterStyle);
                    AddPageNumbers(text, numberFormat, setup);
                });
            });
        }
        else if (footerText is not null)
        {
            Footer(page, setup)
                .AlignCenter()
                .Text(text =>
                {
                    text.DefaultTextStyle(FooterStyle);
                    text.Span(footerText);
                });
        }
        else
        {
            Footer(page, setup)
                .AlignCenter()
                .Text(text =>
                {
                    text.DefaultTextStyle(FooterStyle);
                    AddPageNumbers(text, numberFormat!, setup);
                });
        }
    }

    /// <summary>
    /// The layer the footer is printed on. It is the foreground rather than the footer slot because
    /// the slot stops at the bottom margin, while the footer belongs inside the margin, a little
    /// above the edge of the sheet. The foreground covers the whole page, so the footer is pushed
    /// down to <see cref="FooterInsetMm"/> from the bottom edge and lined up with the text column.
    /// </summary>
    private static IContainer Footer(PageDescriptor page, PageSetup setup)
        => page.Foreground()
            .AlignBottom()
            .PaddingHorizontal(Math.Min(setup.MarginMm, (float)setup.WidthMm / 4), QUnit.Millimetre)
            .PaddingBottom(FooterInsetMm(setup), QUnit.Millimetre);

    /// <summary>
    /// Distance between the footer and the bottom edge of the sheet: half the margin, kept between
    /// three and twelve millimetres so that it neither crowds a narrow margin nor drifts into the
    /// middle of a wide one.
    /// </summary>
    private static float FooterInsetMm(PageSetup setup) => Math.Clamp(setup.MarginMm / 2, 3f, 12f);

    private static DocumentMetadata Metadata(PdfExportOptions options) => new()
    {
        Title = options.Title ?? string.Empty,
        Author = options.Author ?? string.Empty,
        Creator = "Local Book Binder",
    };

    /// <summary>Which chapters start on a new page, to keep every chapter title on an odd page.</summary>
    private sealed record BookPlan(bool[] BlankBefore);

    private sealed record PageSetup(
        QPageSize Size,
        float MarginMm,
        double WidthMm,
        double HeightMm,
        string[] Families,
        double BaseSize,
        string? FooterText,
        string? NumberFormat,
        byte[]? Background,
        string? NumberSection = null,
        PageNumberFormatter? NumberFormatter = null)
    {
        /// <summary>Height of the text area between the top and the bottom margin, in millimetres.</summary>
        public double ContentHeightMm => Math.Max(0, HeightMm - (2 * MarginMm));

        /// <summary>Width of the text area between the left and the right margin, in millimetres.</summary>
        public double ContentWidthMm => Math.Max(0, WidthMm - (2 * MarginMm));
    }

    private static QTextStyle FooterStyle(QTextStyle style) => style.FontSize(9).FontColor(FooterColor);

    /// <summary>Returns null when the page numbers are switched off.</summary>
    private static string? NormalizeNumberFormat(string? format)
    {
        if (format is null)
        {
            return PdfExportOptions.DefaultPageNumberFormat;
        }

        var value = format.Trim();
        if (value.Length == 0 || string.Equals(value, "none", StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        return value;
    }

    /// <summary>
    /// Writes a page number pattern, replacing the {page} and {total} placeholders. Inside a numbered
    /// section both count from the first page of that section, which is how the front matter runs in
    /// roman numerals while the chapters start again at one.
    /// </summary>
    private static void AddPageNumbers(TextDescriptor text, string format, PageSetup setup)
    {
        const string PageToken = "{page}";
        const string TotalToken = "{total}";

        var position = 0;
        while (position < format.Length)
        {
            var pageAt = format.IndexOf(PageToken, position, StringComparison.OrdinalIgnoreCase);
            var totalAt = format.IndexOf(TotalToken, position, StringComparison.OrdinalIgnoreCase);
            var next = pageAt < 0 ? totalAt : totalAt < 0 ? pageAt : Math.Min(pageAt, totalAt);

            if (next < 0)
            {
                text.Span(format[position..]);
                return;
            }

            if (next > position)
            {
                text.Span(format[position..next]);
            }

            if (next == pageAt)
            {
                AddPageNumber(text, setup, current: true);
                position = pageAt + PageToken.Length;
            }
            else
            {
                AddPageNumber(text, setup, current: false);
                position = totalAt + TotalToken.Length;
            }
        }
    }

    /// <summary>
    /// Writes the current page or the total of pages. A page inside a numbered section is counted
    /// within that section; any other page - a cover, or a book laid out without sections - is
    /// counted within the whole document.
    /// </summary>
    private static void AddPageNumber(TextDescriptor text, PageSetup setup, bool current)
    {
        var section = setup.NumberSection;

        var descriptor = current
            ? section is null ? text.CurrentPageNumber() : text.PageNumberWithinSection(section)
            : section is null ? text.TotalPages() : text.TotalPagesWithinSection(section);

        if (setup.NumberFormatter is { } formatter)
        {
            descriptor.Format(formatter);
        }
    }

    /// <summary>
    /// Roman numerals for the front matter. QuestPDF measures the text before it knows any page
    /// numbers and calls the formatter with a null, so an unknown number still has to come back as a
    /// placeholder of a typical width.
    /// </summary>
    private static string RomanNumber(int? number)
    {
        if (number is not { } value || value <= 0)
        {
            return "iii";
        }

        var text = new StringBuilder();
        foreach (var (amount, symbol) in RomanNumerals)
        {
            while (value >= amount)
            {
                text.Append(symbol);
                value -= amount;
            }
        }

        return text.ToString();
    }

    private static float MmToPoints(double millimetres) => (float)(millimetres / 25.4 * 72.0);

    /// <summary>Formatting copied from a WPF inline onto a QuestPDF text style.</summary>
    private readonly record struct RunStyle(
        string Family,
        double Size,
        QFontWeight Weight,
        bool Italic,
        bool Underline,
        bool Strike,
        QColor Color);

    private sealed class BlockWriter
    {
        private readonly ColumnDescriptor _column;
        private readonly string[] _chain;
        private readonly string _family;
        private readonly string? _documentFamily;
        private readonly double _baseSize;
        private readonly double _scale;
        private readonly RunStyle _root;
        private bool _hasContent;

        public BlockWriter(ColumnDescriptor column, string[] chain, double baseSize, double documentSize, string? documentFamily)
        {
            _column = column;
            _chain = chain;
            _family = chain[0];
            _documentFamily = documentFamily;
            _baseSize = baseSize;
            // A requested font size rescales the whole document, so headings stay proportional.
            _scale = documentSize > 0 && baseSize > 0 ? baseSize / documentSize : 1;
            _root = new RunStyle(_family, baseSize, QFontWeight.Normal, false, false, false, QColor.FromRGB(0, 0, 0));
        }

        public void AddBlock(Block block, double indentPt)
        {
            switch (block)
            {
                case Paragraph paragraph:
                    AddParagraph(paragraph, indentPt, null);
                    break;

                case List list:
                    AddList(list, indentPt);
                    break;

                case Section section:
                    foreach (var child in section.Blocks)
                    {
                        AddBlock(child, indentPt);
                    }

                    break;

                case Table table:
                    var text = new TextRange(table.ContentStart, table.ContentEnd).Text;
                    if (!string.IsNullOrWhiteSpace(text))
                    {
                        AddPlainText(text, indentPt);
                    }

                    break;
            }
        }

        private void AddList(List list, double indentPt)
        {
            var index = 1;
            foreach (var item in list.ListItems)
            {
                var marker = Marker(list.MarkerStyle, index++);
                var first = true;
                foreach (var block in item.Blocks)
                {
                    if (block is Paragraph paragraph && first)
                    {
                        AddParagraph(paragraph, indentPt + 18 * DipToPoint, marker);
                        first = false;
                        continue;
                    }

                    AddBlock(block, indentPt + 18 * DipToPoint);
                    first = false;
                }
            }
        }

        /// <summary>WPF DIPs to points; WPF reports unset margins as NaN.</summary>
        private static double Dips(double value)
            => double.IsNaN(value) || double.IsInfinity(value) || value <= 0 ? 0 : value * DipToPoint;

        private static string Marker(TextMarkerStyle style, int index) => style switch
        {
            TextMarkerStyle.Decimal => index.ToString(CultureInfo.InvariantCulture) + ".  ",
            TextMarkerStyle.LowerLatin => (char)('a' + Math.Min(25, index - 1)) + ".  ",
            TextMarkerStyle.UpperLatin => (char)('A' + Math.Min(25, index - 1)) + ".  ",
            _ => "•  "
        };

        private void AddPlainText(string text, double indentPt)
        {
            _hasContent = true;

            _column.Item()
                .PaddingLeft((float)indentPt)
                .Text(target => AddRun(target, text, _root));
        }

        private void AddParagraph(Paragraph source, double indentPt, string? marker)
        {
            if (source.BreakPageBefore && _hasContent)
            {
                _column.Item().PageBreak();
            }

            _hasContent = true;

            var item = _column.Item()
                .PaddingLeft((float)(indentPt + Dips(source.Margin.Left)))
                .PaddingRight((float)Dips(source.Margin.Right))
                .PaddingTop((float)Dips(source.Margin.Top))
                .PaddingBottom((float)Dips(source.Margin.Bottom));

            var alignment = source.TextAlignment;
            var lineHeight = LineHeightMultiplier(source);
            var firstLineIndent = source.TextIndent > 0 ? source.TextIndent * DipToPoint : 0;
            var isEmpty = string.IsNullOrWhiteSpace(new TextRange(source.ContentStart, source.ContentEnd).Text);

            item.Text(text =>
            {
                switch (alignment)
                {
                    case TextAlignment.Center:
                        text.AlignCenter();
                        break;
                    case TextAlignment.Right:
                        text.AlignRight();
                        break;
                    case TextAlignment.Justify:
                        text.Justify();
                        break;
                    default:
                        text.AlignLeft();
                        break;
                }

                if (firstLineIndent > 0)
                {
                    text.ParagraphFirstLineIndentation((float)firstLineIndent, QUnit.Point);
                }

                if (lineHeight is { } multiplier)
                {
                    text.DefaultTextStyle(style => style.LineHeight((float)multiplier));
                }

                if (!string.IsNullOrEmpty(marker))
                {
                    AddRun(text, marker, _root);
                }

                if (isEmpty)
                {
                    AddStyledSpan(text, " ", ToQuestStyle(_root));
                    return;
                }

                AddInlines(text, source.Inlines, null);
            });
        }

        /// <summary>WPF stores an absolute line height in DIPs; QuestPDF wants a font-size multiple.</summary>
        private double? LineHeightMultiplier(Paragraph source)
        {
            var lineHeight = source.LineHeight;
            if (double.IsNaN(lineHeight) || lineHeight <= 0 || lineHeight > 500)
            {
                return null;
            }

            var size = source.FontSize > 0 && !double.IsNaN(source.FontSize) ? source.FontSize * DipToPoint : _baseSize;
            if (size <= 0)
            {
                return null;
            }

            var ratio = lineHeight * DipToPoint / size;
            return ratio is >= 0.9 and <= 4.0 ? ratio : null;
        }

        private void AddInlines(TextDescriptor target, InlineCollection inlines, RunStyle? inherited)
        {
            foreach (var inline in inlines)
            {
                switch (inline)
                {
                    case Run run:
                        AddRun(target, run.Text, Merge(inherited, run));
                        break;

                    case LineBreak:
                        AddStyledSpan(target, "\n", ToQuestStyle(inherited ?? _root));
                        break;

                    case Span span:
                        // Bold, Italic, Underline and Hyperlink all derive from Span.
                        AddInlines(target, span.Inlines, Merge(inherited, span));
                        break;
                }
            }
        }

        private void AddRun(TextDescriptor target, string? text, RunStyle style)
        {
            if (string.IsNullOrEmpty(text))
            {
                return;
            }

            AddStyledSpan(target, text.Replace("\r\n", "\n").Replace('\r', '\n'), ToQuestStyle(style));
        }

        // QuestPDF 2026.9 only styles text through this overload; the obsolete note on it points at
        // an API that no longer exists, so the warning is suppressed here rather than at call sites.
#pragma warning disable CS0618
        private static void AddStyledSpan(TextDescriptor target, string text, QTextStyle style)
            => target.Span(text, style);
#pragma warning restore CS0618

        /// <summary>
        /// The run's own family first, the document family second: QuestPDF walks the list and uses
        /// the first font that has a glyph for each character, so nothing disappears from the page.
        /// A run that merely inherits the document font is left to the document chain, which keeps
        /// the alternative family ahead of it.
        /// </summary>
        private QTextStyle ToQuestStyle(RunStyle style)
        {
            var families = new List<string>(_chain.Length + 1);
            var requested = PdfFonts.FindFamily(style.Family);
            if (requested is not null
                && !string.Equals(requested, _family, StringComparison.OrdinalIgnoreCase)
                && !string.Equals(requested, _documentFamily, StringComparison.OrdinalIgnoreCase))
            {
                families.Add(requested);
            }

            foreach (var family in _chain)
            {
                if (!families.Contains(family, StringComparer.OrdinalIgnoreCase))
                {
                    families.Add(family);
                }
            }

            return QTextStyle.Default
                .FontFamily(families.ToArray())
                .FontSize((float)(style.Size > 0 ? style.Size : _baseSize))
                .FontColor(style.Color)
                .Weight(style.Weight)
                .Italic(style.Italic)
                .Underline(style.Underline)
                .Strikethrough(style.Strike);
        }

        private RunStyle Merge(RunStyle? inherited, Inline inline)
        {
            var current = inherited ?? _root;

            var size = inline.FontSize > 0 && !double.IsNaN(inline.FontSize)
                ? inline.FontSize * DipToPoint * _scale
                : current.Size;

            var color = inline.Foreground is SolidColorBrush
                ? ToQuestColor(inline.Foreground)
                : current.Color;

            return new RunStyle(
                Family: inline.FontFamily?.Source ?? current.Family,
                Size: size,
                Weight: ToWeight(inline.FontWeight),
                Italic: inline.FontStyle != FontStyles.Normal,
                Underline: current.Underline || HasDecoration(inline, TextDecorationLocation.Underline),
                Strike: current.Strike || HasDecoration(inline, TextDecorationLocation.Strikethrough),
                Color: color);
        }

        private static QFontWeight ToWeight(System.Windows.FontWeight weight)
        {
            var openType = weight.ToOpenTypeWeight();
            return openType switch
            {
                <= 150 => QFontWeight.Thin,
                <= 250 => QFontWeight.ExtraLight,
                <= 350 => QFontWeight.Light,
                <= 450 => QFontWeight.Normal,
                <= 550 => QFontWeight.Medium,
                <= 650 => QFontWeight.SemiBold,
                <= 750 => QFontWeight.Bold,
                <= 850 => QFontWeight.ExtraBold,
                <= 925 => QFontWeight.Black,
                _ => QFontWeight.ExtraBlack
            };
        }

        private static bool HasDecoration(Inline inline, TextDecorationLocation location)
        {
            var decorations = inline.TextDecorations;
            if (decorations is null || decorations.Count == 0)
            {
                return false;
            }

            foreach (var decoration in decorations)
            {
                if (decoration.Location == location)
                {
                    return true;
                }
            }

            return false;
        }

        private static QColor ToQuestColor(Brush? brush)
        {
            var color = PdfExport.ToPrintColor(brush);
            return QColor.FromRGB(color.R, color.G, color.B);
        }
    }
}
