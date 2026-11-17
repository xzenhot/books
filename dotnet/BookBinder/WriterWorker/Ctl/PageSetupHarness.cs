using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

using WriterWorker.Configuration;
using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Contents;
using WriterWorker.Parser.PublishedParser.Contents;
using WriterWorker.Views;

namespace WriterWorker.Ctl;

/// <summary>
/// Development harness for the book layout: exports a sample book with and without covers, checks
/// that the named layout configurations round-trip, and renders the setup dialog to PNG so its
/// tabs and footer can be inspected without clicking through the UI.
/// <para>
/// Nothing in the application calls it. To run it, invoke <see cref="TryRunFromEnvironment"/> from
/// a startup path (for example <c>App.OnStartup</c> in the host project) and launch the app with
/// <c>PAGE_SETUP_HARNESS</c> set to the folder the report and PDFs should be written to:
/// </para>
/// <code>
/// if (PageSetupHarness.TryRunFromEnvironment()) { Shutdown(); return; }
/// </code>
/// </summary>
public static class PageSetupHarness
{
    private const string OutputVariable = "PAGE_SETUP_HARNESS";
    private const string DefaultWorkspace = @"D:\lab\github\books\writer\workspaces\pipeline\nouka";

    /// <summary>Runs the harness when <c>PAGE_SETUP_HARNESS</c> names an output folder.</summary>
    public static bool TryRunFromEnvironment()
    {
        var output = Environment.GetEnvironmentVariable(OutputVariable);
        if (string.IsNullOrWhiteSpace(output))
        {
            return false;
        }

        Run(output);
        return true;
    }

    /// <summary>
    /// Writes the covers/no-covers PDFs, the dialog screenshots and <c>report.txt</c> into
    /// <paramref name="outputDirectory"/>.
    /// </summary>
    public static void Run(string outputDirectory, string workspace = DefaultWorkspace)
    {
        Directory.CreateDirectory(outputDirectory);
        var report = new StringBuilder();

        // The harness opens and closes several windows; with the default shutdown mode the first
        // one to close would end the application, so the harness closes it explicitly instead.
        if (Application.Current is { } application)
        {
            application.ShutdownMode = ShutdownMode.OnExplicitShutdown;
        }

        try
        {
            var book = ConfigToModel.FromConfigurationParser(BookContent.Load(workspace));
            report.AppendLine($"book: {book.Title} chapters={book.Chapters.Count}");

            var front = Path.Combine(outputDirectory, "front.png");
            var back = Path.Combine(outputDirectory, "back.png");
            MakeImage(front, Colors.DarkSlateBlue, "FRONT COVER", 900, 1200);
            MakeImage(back, Colors.DarkOliveGreen, "BACK COVER", 900, 1200);

            var options = new PdfExportOptions
            {
                PageWidthMm = 148,
                PageHeightMm = 210,
                MarginMm = 15,
                FontFamily = PdfExport.DefaultFontFamily,
                FooterText = "Nouka",
                PageNumberFormat = PdfExportOptions.DefaultPageNumberFormat,
                Layout = PdfLayout.ChapterPages,
                FrontCoverImagePath = front,
                BackCoverImagePath = back,
                IncludeCovers = true,
                Title = "Nouka"
            };

            var withCovers = Path.Combine(outputDirectory, "with-covers.pdf");
            QuestPdfExport.Save(book, withCovers, options);
            report.AppendLine($"pdf: {withCovers} {new FileInfo(withCovers).Length} bytes");

            var plainOptions = options.Clone();
            plainOptions.IncludeCovers = false;
            plainOptions.FrontCoverImagePath = null;
            plainOptions.BackCoverImagePath = null;
            var withoutCovers = Path.Combine(outputDirectory, "no-covers.pdf");
            QuestPdfExport.Save(book, withoutCovers, plainOptions);
            report.AppendLine($"plain pdf: {withoutCovers} {new FileInfo(withoutCovers).Length} bytes");

            ReportSegmentTitleGap(report, outputDirectory, book, plainOptions);
            ReportFooterPosition(report, outputDirectory, book, options);
            ReportPageGeometry(report, outputDirectory, book, options);
            ReportCoverCentring(report, outputDirectory, book, options);

            // The design page renders the segment layout on a worker thread, so the export has to
            // work away from the UI thread as well.
            var background = Path.Combine(outputDirectory, "background.pdf");
            Task.Run(() => QuestPdfExport.Save(book, background, plainOptions)).GetAwaiter().GetResult();
            report.AppendLine($"background pdf: {background} {new FileInfo(background).Length} bytes");

            ReportConfigurations(report, options);
            ReportBookConfig(report, options, workspace);
            ReportBackCover(report, outputDirectory, options);
            ReportIndex(report, outputDirectory, plainOptions);
            ReportPublished(report, outputDirectory, workspace, plainOptions);
            ReportDesignPage(report, outputDirectory, workspace);
            ReportDialog(report, outputDirectory, options);
        }
        catch (Exception exception)
        {
            report.AppendLine("ERROR: " + exception);
        }

        File.WriteAllText(Path.Combine(outputDirectory, "report.txt"), report.ToString());
    }

    /// <summary>
    /// Reads the published edition that sits next to the pipeline workspace
    /// (<c>...\workspaces\published\{book}\version{n}</c>) and compares it with the pipeline content,
    /// so the published parser can be checked without opening the PDFs.
    /// </summary>
    private static void ReportPublished(
        StringBuilder report,
        string outputDirectory,
        string workspace,
        PdfExportOptions options)
    {
        try
        {
            var name = Path.GetFileName(workspace.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
            var sibling = Path.GetDirectoryName(Path.GetDirectoryName(
                workspace.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)));
            var root = sibling is null ? null : PublishedLibrary.ResolveRoot(Path.Combine(sibling, "published"));
            report.AppendLine($"published root: {root}");

            var books = PublishedLibrary.Scan(root);
            report.AppendLine($"published books: {string.Join(", ", books.Select(book => book.DisplayName))}");

            var entry = books.FirstOrDefault(book => string.Equals(book.FolderName, name, StringComparison.OrdinalIgnoreCase));
            if (entry?.Latest is not { } version)
            {
                report.AppendLine($"published: no version folder for {name}");
                return;
            }

            var published = PublishedContentLoader.Load(version.FolderPath);
            var pipeline = BookContent.Load(workspace);
            report.AppendLine(
                $"published: {entry.FolderName} {version.FolderName} title=\"{published.Title}\" "
                + $"chapters={published.Chapters.Count} segments={published.Chapters.Sum(chapter => chapter.Segments.Count)} "
                + $"publishedAt={published.Progress?.PublishedAt} version={published.Progress?.PublishedVersion}");
            report.AppendLine(
                $"pipeline: title=\"{pipeline.Title}\" chapters={pipeline.Chapters.Count} "
                + $"segments={pipeline.Chapters.Sum(chapter => chapter.Segments.Count)}");

            var differences = CompareChapterText(pipeline, published);
            report.AppendLine($"published text differences: {differences.Count}");
            foreach (var difference in differences.Take(5))
            {
                report.AppendLine("  " + difference);
            }

            var publishedBook = PublishedLibrary.OpenBook(version);
            report.AppendLine(
                $"published model: \"{publishedBook.Title}\" chapters={publishedBook.Chapters.Count} "
                + $"version={publishedBook.Version} stage={publishedBook.Stage} author={publishedBook.Author}");

            // The profile of a published edition carries a copy of the print setup, and records the
            // source its content came from, so the copy can be followed back to the pipeline book.
            report.AppendLine(BookProfile.Load(version.FolderPath) is { } profile
                ? $"published profile: version={profile.Version} name={BookProfile.NameOf(profile)} "
                    + $"source={profile.Source?.BookName}/{profile.Source?.SourceFormat}/"
                    + $"{profile.Source?.SourcePath}/v{profile.Source?.Version} "
                    + $"pages={profile.Book?.Pages?.Count.ToString() ?? "null"}"
                : "published profile: MISSING");
            report.AppendLine($"published profile source resolved: {BookProfile.ContentFolderOf(version.FolderPath) ?? "MISSING"}");

            var page = new BookViewPage(publishedBook, version.FolderPath);
            report.AppendLine(
                $"published page: {page.AssembledText.Length} chars, header=\"{page.HeaderTitle}\", "
                + $"stats=\"{page.HeaderStats}\", status=\"{page.StatusText}\"");

            var path = Path.Combine(outputDirectory, "published.pdf");
            QuestPdfExport.Save(publishedBook, path, options);
            var baseline = Path.Combine(outputDirectory, "no-covers.pdf");
            var same = File.Exists(baseline)
                && File.ReadAllBytes(baseline).SequenceEqual(File.ReadAllBytes(path));
            report.AppendLine($"published pdf: {path} {new FileInfo(path).Length} bytes (same as pipeline: {same})");
        }
        catch (Exception exception)
        {
            report.AppendLine("published ERROR: " + exception.Message);
        }
    }

    /// <summary>Compares the published segment texts with the pipeline texts, chapter by chapter.</summary>
    private static List<string> CompareChapterText(BookContent pipeline, BookContent published)
    {
        var differences = new List<string>();
        foreach (var chapter in published.Chapters)
        {
            var source = pipeline.Chapters.FirstOrDefault(candidate =>
                string.Equals(candidate.Name, chapter.Name, StringComparison.OrdinalIgnoreCase));
            if (source is null)
            {
                differences.Add($"chapter {chapter.Name} is missing from the pipeline");
                continue;
            }

            if (!string.Equals(source.Title, chapter.Title, StringComparison.Ordinal))
            {
                differences.Add($"chapter {chapter.Name} title: \"{source.Title}\" vs \"{chapter.Title}\"");
            }

            if (source.Segments.Count != chapter.Segments.Count)
            {
                differences.Add($"chapter {chapter.Name} segments: {source.Segments.Count} vs {chapter.Segments.Count}");
            }

            foreach (var segment in chapter.Segments)
            {
                var origin = source.GetSegment(segment.Index);
                if (origin is null)
                {
                    differences.Add($"chapter {chapter.Name} segment {segment.Index} is missing from the pipeline");
                    continue;
                }

                if (!string.Equals(origin.DisplayText?.Trim(), segment.DisplayText?.Trim(), StringComparison.Ordinal))
                {
                    differences.Add($"chapter {chapter.Name} segment {segment.Index} text differs");
                }
            }
        }

        return differences;
    }

    /// <summary>
    /// Renders the first segment page of the book layout and reports the rows of text on it, so the
    /// blank line kept under a segment title can be checked without opening the PDF.
    /// </summary>
    private static void ReportSegmentTitleGap(
        StringBuilder report,
        string outputDirectory,
        Book book,
        PdfExportOptions options)
    {
        // Page 1 is the chapter title page, so page 2 is the first page of segment text.
        var document = QuestPdfExport.CreateDocument(book, options);
        var pages = QuestPDF.Fluent.GenerateExtensions
            .GenerateImages(document, QuestPDF.Infrastructure.ImageGenerationSettings.Default)
            .Take(2)
            .ToList();

        if (pages.Count < 2)
        {
            report.AppendLine($"segment page: only {pages.Count} page(s) rendered");
            return;
        }

        var path = Path.Combine(outputDirectory, "segment-page.png");
        File.WriteAllBytes(path, pages[1]);

        using var stream = File.OpenRead(path);
        var frame = BitmapFrame.Create(stream, BitmapCreateOptions.None, BitmapCacheOption.OnLoad);
        var stride = frame.PixelWidth * 4;
        var pixels = new byte[stride * frame.PixelHeight];
        frame.CopyPixels(pixels, stride, 0);

        var rows = new List<int>();
        for (var y = 0; y < frame.PixelHeight; y++)
        {
            for (var x = 0; x < frame.PixelWidth; x++)
            {
                var offset = (y * stride) + (x * 4);
                if (pixels[offset] < 100 && pixels[offset + 1] < 100 && pixels[offset + 2] < 100)
                {
                    rows.Add(y);
                    break;
                }
            }
        }

        var bands = new List<(int Top, int Bottom)>();
        foreach (var row in rows)
        {
            if (bands.Count > 0 && row - bands[^1].Bottom <= 2)
            {
                bands[^1] = (bands[^1].Top, row);
            }
            else
            {
                bands.Add((row, row));
            }
        }

        report.AppendLine($"segment page: {path} {frame.PixelWidth}x{frame.PixelHeight} bands={bands.Count}");
        report.AppendLine($"segment page bands: {string.Join(", ", bands.Take(6).Select(band => $"{band.Top}-{band.Bottom}"))}");

        if (bands.Count >= 2)
        {
            var gap = bands[1].Top - bands[0].Bottom;
            report.AppendLine($"segment title gap: {gap}px between the title and the first line");
        }
    }

    /// <summary>
    /// Reports where the footer lands on a body page. The footer is printed inside the bottom
    /// margin, so it is looked for below the bottom margin line: nothing should be there but the
    /// footer itself.
    /// </summary>
    private static void ReportFooterPosition(
        StringBuilder report,
        string outputDirectory,
        Book book,
        PdfExportOptions options)
    {
        var document = QuestPdfExport.CreateDocument(book, options);
        var page = QuestPDF.Fluent.GenerateExtensions
            .GenerateImages(document, new QuestPDF.Infrastructure.ImageGenerationSettings { RasterDpi = 144 })
            .Skip(1)
            .FirstOrDefault();

        if (page is null)
        {
            report.AppendLine("footer: no body page rendered");
            return;
        }

        var path = Path.Combine(outputDirectory, "footer-page.png");
        File.WriteAllBytes(path, page);
        var pixels = ReadPixels(path, out var width, out var height);

        var marginRow = (int)Math.Ceiling(height * options.MarginMm / options.PageHeightMm);
        int top = height, bottom = -1;
        for (var y = marginRow; y < height; y++)
        {
            for (var x = 0; x < width; x++)
            {
                var offset = ((y * width) + x) * 4;
                if (pixels[offset] < 200 && pixels[offset + 1] < 200 && pixels[offset + 2] < 200)
                {
                    if (y < top) top = y;
                    if (y > bottom) bottom = y;
                    break;
                }
            }
        }

        var mmPerPixel = options.PageHeightMm / height;
        var expected = Math.Clamp(options.MarginMm / 2, 3, 12);
        report.AppendLine(bottom < 0
            ? "footer: nothing printed below the bottom margin"
            : $"footer: {(height - 1 - bottom) * mmPerPixel:F1}mm from the bottom edge to the last line, {(height - 1 - top) * mmPerPixel:F1}mm to the first, margin {options.MarginMm}mm so {expected:F1}mm was expected");
    }

    /// <summary>
    /// Renders a cover whose source image carries a black cross through its middle, then reports the
    /// gaps between the printed picture and the four edges and where the cross landed. A cover that
    /// fills the sheet leaves no gap at any edge and keeps the cross on the middle of the sheet,
    /// whatever the shape of the source.
    /// </summary>
    private static void ReportCoverCentring(
        StringBuilder report,
        string outputDirectory,
        Book book,
        PdfExportOptions options)
    {
        // One source is wider than the page and one is taller, so both directions of the stretch are
        // exercised.
        ReportCoverCross(report, outputDirectory, book, options, "wide", 1200, 1400);
        ReportCoverCross(report, outputDirectory, book, options, "tall", 1000, 2000);
    }

    private static void ReportCoverCross(
        StringBuilder report,
        string outputDirectory,
        Book book,
        PdfExportOptions options,
        string label,
        int sourceWidth,
        int sourceHeight)
    {
        var cover = Path.Combine(outputDirectory, $"centring-cover-{label}.png");
        MakeCentringImage(cover, sourceWidth, sourceHeight);

        var single = options.Clone();
        single.FrontCoverImagePath = cover;
        single.BackCoverImagePath = null;
        single.BackgroundImagePath = null;

        var page = QuestPDF.Fluent.GenerateExtensions
            .GenerateImages(
                QuestPdfExport.CreateDocument(book, single),
                new QuestPDF.Infrastructure.ImageGenerationSettings { RasterDpi = 144 })
            .First();

        var path = Path.Combine(outputDirectory, $"centring-page-{label}.png");
        File.WriteAllBytes(path, page);
        var pixels = ReadPixels(path, out var width, out var height);

        // The cross is the only dark ink on the sheet, so the middle of its pixels is the middle of
        // the picture: it belongs on the middle of the sheet however the source was shaped.
        double sumX = 0, sumY = 0;
        var dark = 0;
        for (var y = 0; y < height; y++)
        {
            for (var x = 0; x < width; x++)
            {
                if (!IsDark(pixels, ((y * width) + x) * 4))
                {
                    continue;
                }

                sumX += x;
                sumY += y;
                dark++;
            }
        }

        // The picture is stretched over the page, so it must reach all four edges of the sheet.
        var bounds = InkBounds(pixels, width, height);

        report.AppendLine(dark == 0
            ? $"cover {label}: nothing printed"
            : $"cover {label} {sourceWidth}x{sourceHeight} on a {width}x{height} sheet: printed left={bounds.Left} right={bounds.Right} top={bounds.Top} bottom={bounds.Bottom} (0 expected everywhere), cross middle at {sumX / dark:F1} of {(width - 1) / 2.0:F1} across and {sumY / dark:F1} of {(height - 1) / 2.0:F1} down");
    }

    /// <summary>The empty gaps between the printed ink and each edge of the sheet.</summary>
    private static (int Left, int Top, int Right, int Bottom) InkBounds(byte[] pixels, int width, int height)
    {
        int minX = width, minY = height, maxX = -1, maxY = -1;
        for (var y = 0; y < height; y++)
        {
            for (var x = 0; x < width; x++)
            {
                var offset = ((y * width) + x) * 4;
                if (pixels[offset] > 245 && pixels[offset + 1] > 245 && pixels[offset + 2] > 245)
                {
                    continue;
                }

                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }
        }

        return maxX < 0
            ? (width, height, -1, -1)
            : (minX, minY, width - 1 - maxX, height - 1 - maxY);
    }

    private static bool IsDark(byte[] pixels, int offset)
        => pixels[offset] < 60 && pixels[offset + 1] < 60 && pixels[offset + 2] < 60;

    /// <summary>
    /// Renders the covers and a body page and reports where the printed image sits on the sheet, so
    /// a cover or a background image that stops at the margin, or that is letterboxed instead of
    /// covering the page, is caught without opening the PDF.
    /// </summary>
    private static void ReportPageGeometry(
        StringBuilder report,
        string outputDirectory,
        Book book,
        PdfExportOptions options)
    {
        // Both images are a different shape from the page (0.75 and 0.76 against 0.70) and carry a
        // red strip down each side. A background is a full bleed, so it is cropped to the page
        // shape and the strips vanish; a cover is stretched to the page shape, so every pixel of it
        // is still printed and the ink reaches all four edges.
        var background = Path.Combine(outputDirectory, "page-background.png");
        MakeBandedImage(background, Colors.DarkSlateBlue, "BACKGROUND", 800, 1050);

        var cover = Path.Combine(outputDirectory, "bleed-cover.jpg");
        MakeBandedImage(cover, Colors.DarkSlateBlue, "COVER", 900, 1200);

        var withBackground = options.Clone();
        withBackground.BackgroundImagePath = background;
        withBackground.FrontCoverImagePath = cover;
        withBackground.BackCoverImagePath = cover;

        var pages = QuestPDF.Fluent.GenerateExtensions
            .GenerateImages(
                QuestPdfExport.CreateDocument(book, withBackground),
                new QuestPDF.Infrastructure.ImageGenerationSettings { RasterDpi = 72 })
            .ToList();

        report.AppendLine($"geometry pages: {pages.Count}");

        var front = Path.Combine(outputDirectory, "cover-page.png");
        var body = Path.Combine(outputDirectory, "body-page.png");
        var back = Path.Combine(outputDirectory, "back-cover-page.png");

        ReportImageBounds(report, "front cover ink", pages[0], front);
        ReportImageBounds(report, "body page ink", pages[Math.Min(1, pages.Count - 1)], body);
        ReportImageBounds(report, "back cover ink", pages[^1], back);

        ReportBandPixels(report, "front cover strip", front);
        ReportBandPixels(report, "body page strip", body);
        ReportBandPixels(report, "back cover strip", back);
    }

    /// <summary>
    /// Counts the pixels of the red strip that a banded test image carries down its left and right
    /// edges. A full bleed crops it away, which is how a background is printed; a cover is stretched
    /// to the page shape, so every pixel of it is still on the sheet.
    /// </summary>
    private static void ReportBandPixels(StringBuilder report, string label, string path)
    {
        var pixels = ReadPixels(path, out var width, out var height);
        var strip = 0;
        for (var y = 0; y < height; y++)
        {
            for (var x = 0; x < width; x++)
            {
                var offset = ((y * width) + x) * 4;
                if (pixels[offset + 2] > 200 && pixels[offset + 1] < 80 && pixels[offset] < 80)
                {
                    strip++;
                }
            }
        }

        report.AppendLine($"{label}: {strip} pixels of the cropped edge");
    }

    /// <summary>Reports the box the printed pixels occupy on a rendered page.</summary>
    private static void ReportImageBounds(StringBuilder report, string label, byte[] png, string path)
    {
        File.WriteAllBytes(path, png);

        var pixels = ReadPixels(path, out var width, out var height);

        var bounds = InkBounds(pixels, width, height);
        report.AppendLine(bounds.Right < 0
            ? $"{label}: {width}x{height} nothing printed"
            : $"{label}: {width}x{height} (left={bounds.Left} right={bounds.Right} top={bounds.Top} bottom={bounds.Bottom})");
    }

    private static byte[] ReadPixels(string path, out int width, out int height)
    {
        using var stream = File.OpenRead(path);
        var frame = BitmapFrame.Create(stream, BitmapCreateOptions.None, BitmapCacheOption.OnLoad);
        width = frame.PixelWidth;
        height = frame.PixelHeight;

        // Normalise the channel order so the checks below can read blue, green and red at 0, 1, 2.
        var converted = new FormatConvertedBitmap(frame, PixelFormats.Bgra32, null, 0);
        var pixels = new byte[width * height * 4];
        converted.CopyPixels(pixels, width * 4, 0);
        return pixels;
    }

    private static void ReportConfigurations(StringBuilder report, PdfExportOptions options)
    {
        var file = Path.Combine(Path.GetTempPath(), "LocalBookBinder-harness-layout.json");
        BookLayout.Create("Harness Layout", options, "written by the harness").Save(file);
        var loaded = BookLayout.Load(file);
        report.AppendLine(loaded is null
            ? "config file load: MISSING"
            : $"config file load: {loaded.Name} v{loaded.Version} {loaded.Options.PageWidthMm}x{loaded.Options.PageHeightMm} cover={loaded.Options.FrontCoverImagePath} description={loaded.Description}");
        report.AppendLine($"config file json: {new FileInfo(file).Length} bytes, bad json rejected={BookLayout.FromJson("{ not a layout") is null}, missing file={BookLayout.Load(Path.Combine(Path.GetTempPath(), "no-such-layout.json")) is null}");
        File.Delete(file);
    }

    /// <summary>
    /// Checks that the print setup of a book lives in its <c>profile.json</c> while the pipeline state
    /// stays in <c>config.json</c>: a book that still keeps its setup in <c>config.json</c> is moved
    /// onto a profile when it is read and those sections are taken out of the file, a layout written
    /// into the book leaves the pipeline keys alone, and a broken profile is backed up instead of
    /// dropped.
    /// </summary>
    private static void ReportBookConfig(StringBuilder report, PdfExportOptions options, string workspace)
    {
        var folder = Path.Combine(Path.GetTempPath(), "LocalBookBinder-harness-book");

        if (Directory.Exists(folder))
        {
            Directory.Delete(folder, recursive: true);
        }

        Directory.CreateDirectory(folder);

        var configPath = WriterConfiguration.PathIn(folder);
        var profilePath = BookProfile.PathIn(folder);

        var source = Path.Combine(workspace, "config.json");
        if (File.Exists(source))
        {
            File.Copy(source, configPath, overwrite: true);
        }

        var seeded = WriterConfiguration.Load(folder);
        report.AppendLine($"book config seeded: file={File.Exists(configPath)} profile={File.Exists(profilePath)}");
        report.AppendLine($"profile layout: folder={BookProfile.ProfileFolderOf(folder)} pages={BookProfile.PagesFolderIn(folder)} profiles={BookProfile.ProfilesFolderIn(folder)}");
        report.AppendLine(seeded is null
            ? "book model: MISSING"
            : $"book model: title={seeded.Title} language={seeded.Language} book_name={seeded.BookName} form={seeded.Form} chapters={seeded.Chapters.Count} total={seeded.TotalChapters} completed={seeded.CompletedChapters} written={seeded.WrittenChapters} published={seeded.Published} version={seeded.PublishedVersion} current={seeded.CurrentChapter ?? "null"} legacy_display={seeded.Layout is not null} legacy_pages={seeded.Pages?.Count.ToString() ?? "null"} legacy_book={seeded.Book is not null} legacy_profile={seeded.Profile ?? "null"} extra={string.Join(",", seeded.AdditionalProperties?.Keys.Select(key => key) ?? Enumerable.Empty<string>())}");
        report.AppendLine($"book model chapters: {string.Join(" | ", (seeded?.Chapters ?? []).Select(chapter => $"{chapter.ChapterNumber}:{chapter.Topic}[{chapter.Category}/{chapter.Status}/{chapter.FilePath}]={chapter.Segments.Count}"))}");

        var firstSegment = seeded?.Chapters.FirstOrDefault()?.Segments.FirstOrDefault();
        report.AppendLine(firstSegment is null
            ? "book model segment: MISSING"
            : $"book model segment: {firstSegment.SegmentNumber} {firstSegment.SegmentTitle} {firstSegment.FilePath} validated={firstSegment.Validated}");

        // Reading the book moves the print setup it still keeps out of config.json.
        var migrated = BookProfile.Load(folder);
        report.AppendLine($"migration: profile={File.Exists(profilePath)} version={migrated?.Version} name={BookProfile.NameOf(migrated)} width={migrated?.Book?.Options?.PageWidthMm} pages={migrated?.Book?.Pages?.Count.ToString() ?? "null"} author={migrated?.Book?.Author ?? "null"}");

        if (File.Exists(configPath))
        {
            using var document = JsonDocument.Parse(File.ReadAllText(configPath));
            var root = document.RootElement;
            report.AppendLine($"book config after the migration: keys={string.Join(", ", root.EnumerateObject().Select(property => property.Name))}");
            report.AppendLine($"book config print sections gone: display={!root.TryGetProperty(WriterConfiguration.DisplaySection, out _)} overriden={!root.TryGetProperty(WriterConfiguration.BookSection, out _)} pages={!root.TryGetProperty(WriterConfiguration.PagesSection, out _)} profile={!root.TryGetProperty(WriterConfiguration.ProfileSection, out _)}");
        }
        else
        {
            report.AppendLine("book config after the migration: absent, the workspace keeps its book in book.json");
        }
        report.AppendLine($"book name: {BookLayout.BookName(folder)}");

        BookLayout.Create("Harness Layout", options, "written by the harness").SaveToBook(folder);

        using (var document = JsonDocument.Parse(File.ReadAllText(profilePath)))
        {
            var root = document.RootElement;
            report.AppendLine($"book profile keys: {string.Join(", ", root.EnumerateObject().Select(property => property.Name))}");
            report.AppendLine(root.TryGetProperty(BookProfile.BookSection, out var book) && book.ValueKind == JsonValueKind.Object
                ? $"book profile book keys: {string.Join(", ", book.EnumerateObject().Select(property => property.Name))}"
                : "book profile book keys: MISSING");

            // The profile records the folder the content is printed from, so a copy that travels into a
            // published edition can still be followed back to the book.
            report.AppendLine(root.TryGetProperty(BookProfile.SourceSection, out var profileSource) && profileSource.ValueKind == JsonValueKind.Object
                ? $"book profile source: keys={string.Join(", ", profileSource.EnumerateObject().Select(property => property.Name))} "
                    + $"book_name={Text(profileSource, "book_name")} source_format={Text(profileSource, "source_format")} "
                    + $"source_path={Text(profileSource, "source_path")} version={Text(profileSource, "version")}"
                : "book profile source: MISSING");
        }

        report.AppendLine($"book profile source resolved: {BookProfile.ContentFolderOf(folder) ?? "none"}");

        var loaded = BookLayout.LoadFromBook(folder);
        report.AppendLine(loaded is null
            ? "book layout load: MISSING"
            : $"book layout load: {loaded.Name} {loaded.Options.PageWidthMm}x{loaded.Options.PageHeightMm} font={loaded.Options.FontFamily} footer={loaded.Options.FooterText} covers={loaded.Options.IncludeCovers} front={loaded.Options.FrontCoverImagePath}");

        // A key the pipeline added to config.json has to survive the write of a layout, because the
        // two files are separate now.
        if (File.Exists(configPath))
        {
            var nodes = JsonNode.Parse(File.ReadAllText(configPath))!.AsObject();
            nodes["future_pipeline_key"] = "kept";
            nodes["chapters"]!.AsArray()[0]!["future_chapter_key"] = 7;
            File.WriteAllText(configPath, nodes.ToJsonString());
        }

        var second = BookLayout.Create("Harness Layout", options, "second write");
        second.Options.PageWidthMm = 105;
        second.SaveToBook(folder);

        if (File.Exists(configPath))
        {
            using var document = JsonDocument.Parse(File.ReadAllText(configPath));
            var root = document.RootElement;
            report.AppendLine($"book config kept: keys={root.EnumerateObject().Count()} future={root.TryGetProperty("future_pipeline_key", out var future) && future.GetString() == "kept"} chapter_future={root.GetProperty("chapters")[0].TryGetProperty("future_chapter_key", out var chapterFuture) && chapterFuture.GetInt32() == 7} chapters={root.GetProperty("chapters").GetArrayLength()} segments={root.GetProperty("chapters")[0].GetProperty("segments").GetArrayLength()} display={root.TryGetProperty(WriterConfiguration.DisplaySection, out _)}");
        }

        report.AppendLine($"book profile rewrite: width={BookLayout.LoadFromBook(folder)?.Options.PageWidthMm} description={BookLayout.LoadFromBook(folder)?.Description}");

        var rewritten = WriterConfiguration.Load(folder);
        report.AppendLine($"book model rewrite: title={rewritten?.Title} chapters={rewritten?.Chapters.Count} segments={rewritten?.Chapters.Sum(chapter => chapter.Segments.Count)} display={rewritten?.Layout is not null}");

        report.AppendLine($"book config missing: {BookLayout.LoadFromBook(Path.Combine(Path.GetTempPath(), "no-such-book")) is null}");

        var broken = Path.Combine(Path.GetTempPath(), "LocalBookBinder-harness-broken");
        Directory.CreateDirectory(broken);
        Directory.CreateDirectory(Path.GetDirectoryName(BookProfile.PathIn(broken))!);
        File.WriteAllText(BookProfile.PathIn(broken), "{ not json");
        BookLayout.Create("Harness Layout", options).SaveToBook(broken);
        report.AppendLine($"broken book profile: backup={File.Exists(BookProfile.PathIn(broken) + BookProfile.BackupSuffix)} layout={BookLayout.LoadFromBook(broken) is not null}");

        Directory.Delete(folder, recursive: true);
        Directory.Delete(broken, recursive: true);
    }

    /// <summary>
    /// Checks that the back cover is a part of the book of its own: an image in
    /// <c>pages/backcover</c> is recorded as an image page and prints after every other page, so
    /// adding one adds exactly one page at the end of the book.
    /// </summary>
    private static void ReportBackCover(StringBuilder report, string outputDirectory, PdfExportOptions options)
    {
        var bookFolder = Path.Combine(Path.GetTempPath(), "LocalBookBinder-harness-backcover");

        if (Directory.Exists(bookFolder))
        {
            Directory.Delete(bookFolder, recursive: true);
        }

        Directory.CreateDirectory(Path.Combine(PagesOf(bookFolder), "cover"));

        // The folder is given a front cover and a configuration of its own first, so it is not seeded
        // from the profile and only the pages the check adds are in it.
        MakeImage(Path.Combine(PagesOf(bookFolder), "cover", "front.jpg"), Colors.DarkSlateBlue, "FRONT", 600, 800);
        PageStore.Save(bookFolder, BookPages.DefaultGroups());
        PageStore.Ensure(bookFolder);

        var single = options.Clone();
        single.IncludeCovers = true;
        single.FrontCoverImagePath = null;
        single.BackCoverImagePath = null;

        var before = Path.Combine(outputDirectory, "back-cover-before.pdf");
        QuestPdfExport.Save(BookOf(bookFolder, options.Title ?? "Back cover"), before, single);
        report.AppendLine($"back cover before: pages={CountPagesOf(before)} groups={DescribeGroups(bookFolder)}");

        MakeImage(Path.Combine(PagesOf(bookFolder), "backcover", "back.jpg"), Colors.DarkOliveGreen, "BACK", 600, 800);
        PageStore.Ensure(bookFolder);
        report.AppendLine($"back cover files: {DescribeFiles(bookFolder)}");

        var after = Path.Combine(outputDirectory, "back-cover-after.pdf");
        QuestPdfExport.Save(BookOf(bookFolder, options.Title ?? "Back cover"), after, single);
        report.AppendLine($"back cover after: pages={CountPagesOf(after)} groups={DescribeGroups(bookFolder)}");
        report.AppendLine($"back cover role: {BookPages.RoleOf("pages/backcover/")} format={BookPages.FormatOf(PageGroupRole.BackCover)} order={BookPages.DefaultOrderOf(PageGroupRole.BackCover)}");
        report.AppendLine($"back cover covers: {PageStore.Covers(bookFolder)}");
        report.AppendLine($"back cover pages: {DescribePages(bookFolder)}");
    }

    /// <summary>Folder the pages of a harness book are kept in: the pages folder of its print profile.</summary>
    private static string PagesOf(string bookFolder) => PageStore.FolderIn(bookFolder);

    /// <summary>
    /// Checks that the index is written from the chapters of the book: the title of every chapter
    /// with the titles of its segments under it and two blank lines between one chapter and the next,
    /// packed into as many pages as the text area of the page setup holds. A book of many chapters
    /// needs more than one page, and the export prints the pages that were written where it used to
    /// print the two it reserves for the index. Building the index again replaces the pages of an
    /// earlier build instead of adding to them.
    /// </summary>
    private static void ReportIndex(StringBuilder report, string outputDirectory, PdfExportOptions options)
    {
        var bookFolder = Path.Combine(Path.GetTempPath(), "LocalBookBinder-harness-index");

        if (Directory.Exists(bookFolder))
        {
            Directory.Delete(bookFolder, recursive: true);
        }

        Directory.CreateDirectory(PagesOf(bookFolder));
        PageStore.Save(bookFolder, BookPages.DefaultGroups());
        PageStore.Ensure(bookFolder);

        var before = Path.Combine(outputDirectory, "index-before.pdf");
        QuestPdfExport.Save(BookOf(bookFolder, options.Title ?? "Index"), before, options);
        report.AppendLine($"index before: pages={CountPagesOf(before)} groups={DescribeGroups(bookFolder)}");

        // Chapters of growing length, so the titles and the segments they list fill more than one
        // page and the break between the pages falls in the middle of a chapter.
        var chapters = new List<Chapter>();

        for (var index = 1; index <= 6; index++)
        {
            var chapter = index;
            chapters.Add(new Chapter
            {
                Index = chapter,
                Title = $"Chapter {chapter}: the {new string('a', chapter * 4)} water",
                Segments = Enumerable.Range(1, chapter + 2)
                    .Select(segment => new Segment
                    {
                        Index = segment,
                        Title = $"Segment {chapter}.{segment} of the {new string('b', segment * 4)} river",
                        Body = $"The body of segment {chapter}.{segment}."
                    })
                    .ToList()
            });
        }

        // A segment with no text prints no page, so it has no line in the index either, and a chapter
        // that carries only a name is indexed under it.
        chapters[2].Segments.Add(new Segment { Index = 99, Title = "Segment without a body" });
        chapters.Add(new Chapter { Index = 7, Name = "The last chapter", Segments = [] });

        var written = IndexPages.Write(bookFolder, chapters, options);
        report.AppendLine($"index pages: count={written.Count} files=[{string.Join(", ", written.Select(path => $"{path}={SizeOf(bookFolder, path)}"))}]");

        foreach (var path in written)
        {
            report.AppendLine($"index page {BookPages.NameOfFile(path)}: {DescribeDesign(bookFolder, path)}");
        }

        report.AppendLine($"index profile: {DescribePages(bookFolder)}");

        var after = Path.Combine(outputDirectory, "index-after.pdf");
        QuestPdfExport.Save(BookOf(bookFolder, options.Title ?? "Index"), after, options);
        var expected = CountPagesOf(before) - 2 + written.Count;
        report.AppendLine($"index after: pages={CountPagesOf(after)} expected={expected} {(CountPagesOf(after) == expected ? "OK" : "MISMATCH")}");

        // Every page is packed to the height of the text area, so a page that takes a second sheet is
        // the one thing the packing must never do: the book would print more sheets than it records.
        var spilled = 0;

        foreach (var path in written)
        {
            PageStore.ReplaceFiles(bookFolder, PageGroupRole.Index, [path]);
            var single = Path.Combine(outputDirectory, $"index-page-{BookPages.NameOfFile(path)}.pdf");
            QuestPdfExport.Save(BookOf(bookFolder, options.Title ?? "Index"), single, options);
            spilled += CountPagesOf(single) == CountPagesOf(before) - 1 ? 0 : 1;
        }

        report.AppendLine($"index sheets: pages={written.Count} spilled={spilled}");
        PageStore.ReplaceFiles(bookFolder, PageGroupRole.Index, written);

        // A book that loses chapters loses the index pages it no longer fills, and the profile records
        // only the pages the build wrote.
        var rebuilt = IndexPages.Write(bookFolder, chapters.Take(1).ToList(), options);
        report.AppendLine($"index rebuilt for one chapter: pages=[{string.Join(", ", rebuilt)}] folder=[{string.Join(", ", IndexFilesOf(bookFolder))}] profile={DescribePages(bookFolder)}");

        Directory.Delete(bookFolder, recursive: true);
    }

    /// <summary>The index files a book folder holds on disk, so the report shows the pages a rebuild left behind.</summary>
    private static IEnumerable<string> IndexFilesOf(string bookFolder)
    {
        var folder = Path.Combine(PagesOf(bookFolder), "index");

        return Directory.Exists(folder)
            ? Directory.GetFiles(folder).Select(Path.GetFileName).OfType<string>().OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
            : [];
    }

    /// <summary>Size of a page file of <paramref name="bookFolder"/>, or <c>MISSING</c> when it is not there.</summary>
    private static string SizeOf(string bookFolder, string relativePath) =>
        BookPages.Resolve(BookProfile.ProfileFolderOf(bookFolder), relativePath) is { } path && File.Exists(path)
            ? new FileInfo(path).Length + " bytes"
            : "MISSING";

    /// <summary>
    /// A page design read back from its file, paragraph by paragraph, so the report shows the lines
    /// the index prints and the size each of them is set in.
    /// </summary>
    private static string DescribeDesign(string bookFolder, string relativePath)
    {
        if (BookPages.Resolve(BookProfile.ProfileFolderOf(bookFolder), relativePath) is not { } path || !File.Exists(path))
        {
            return "MISSING";
        }

        try
        {
            var document = RtfExport.LoadDocument(path);
            var paragraphs = document.Blocks.OfType<Paragraph>().ToList();
            var lines = paragraphs.Select(paragraph =>
            {
                var text = new TextRange(paragraph.ContentStart, paragraph.ContentEnd).Text.Trim();
                var size = paragraph.Inlines.OfType<Run>().FirstOrDefault()?.FontSize ?? paragraph.FontSize;

                return text.Length == 0 ? "-" : $"'{text}'@{size:0.#}";
            });

            return $"paragraphs={paragraphs.Count} [{string.Join(", ", lines)}]";
        }
        catch (Exception exception) when (exception is not OutOfMemoryException)
        {
            return "unreadable: " + exception.Message;
        }
    }

    /// <summary>A string member of a JSON object, or <c>null</c> when it is absent or not a string.</summary>
    private static string? Text(JsonElement element, string name) =>
        element.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    /// <summary>The book of a page folder, with no chapters, so only the pages of the folder print.</summary>
    private static Book BookOf(string bookFolder, string title) => new()
    {
        Title = title,
        FolderPath = bookFolder,
        Chapters = []
    };

    /// <summary>The parts of a book folder and the pages they hold, as the configuration records them.</summary>
    private static string DescribeFiles(string bookFolder) =>
        string.Join(", ", PageStore.Load(bookFolder)
            .SelectMany(group => group.Files)
            .Select(file => $"{file.FilePath}="
                + (BookPages.Resolve(bookFolder, file.FilePath) is { } path && File.Exists(path))));

    /// <summary>The parts of a book folder and the pages they hold, as the configuration records them.</summary>
    private static string DescribeGroups(string bookFolder) =>
        string.Join(", ", PageStore.Load(bookFolder).Select(group => $"{group.Role}={group.Files.Count}"));

    /// <summary>
    /// The number of pages of a saved PDF, counted from the page objects of the file, because the
    /// number of images the document renders is not the number of pages it prints.
    /// </summary>
    private static int CountPagesOf(string path)
    {
        var text = Encoding.Latin1.GetString(File.ReadAllBytes(path));

        return System.Text.RegularExpressions.Regex.Matches(text, @"/Type\s*/Page[^s]").Count;
    }

    private static void ReportDesignPage(StringBuilder report, string outputDirectory, string workspace)
    {
        var page = new BookViewPage(workspace);
        var window = new Window
        {
            Title = "Book design page",
            Content = page,
            Width = 1000,
            Height = 700,
            WindowStartupLocation = WindowStartupLocation.CenterScreen,
        };

        window.Show();
        Pump(window, () => window.IsLoaded, 5000);
        Pump(window, () => false, 500);

        var host = FindChildByName<Border>(page, "ProgressHost");
        var bar = FindChildByName<ProgressBar>(page, "ExportProgressBar");
        var text = FindChildByName<TextBlock>(page, "ProgressText");
        report.AppendLine($"design page progress: host={host is not null} bar={bar is not null} text={text is not null} visibility={host?.Visibility.ToString() ?? "?"}");

        page.ShowProgress("Generating nouka.pdf...");
        Pump(window, () => false, 400);
        report.AppendLine($"design page progress shown: visibility={host?.Visibility.ToString() ?? "?"} indeterminate={bar?.IsIndeterminate} value={bar?.Value} text={text?.Text}");
        report.AppendLine($"design page progress bounds: host={Describe(host, window)} bar={Describe(bar, window)} text={Describe(text, window)}");
        Capture(window, Path.Combine(outputDirectory, "design-page-progress.png"));

        page.ShowProgress("Generating nouka.pdf...", 0.4);
        Pump(window, () => false, 300);
        report.AppendLine($"design page progress determinate: indeterminate={bar?.IsIndeterminate} value={bar?.Value}");
        Capture(window, Path.Combine(outputDirectory, "design-page-progress-value.png"));

        page.HideProgress();
        Pump(window, () => false, 400);
        report.AppendLine($"design page progress hidden: visibility={host?.Visibility.ToString() ?? "?"} text='{text?.Text}'");

        window.Close();
    }

    private static void ReportDialog(StringBuilder report, string outputDirectory, PdfExportOptions options)
    {
        var bookFolder = Path.Combine(Path.GetTempPath(), "LocalBookBinder-harness-dialog");
        Directory.CreateDirectory(bookFolder);
        var profilePath = BookLayout.BookProfilePath(bookFolder);
        var profileFolder = Path.GetDirectoryName(profilePath);
        if (profileFolder is not null && Directory.Exists(profileFolder))
        {
            Directory.Delete(profileFolder, recursive: true);
        }

        // The dialog lists the pages of the book folder, so the folder is given the pages of a book
        // that was set up before the dialog opens.
        var model = BookLayout.LoadBook(bookFolder);
        PageStore.EnsureDesigns(bookFolder, PageGroupRole.Blurb, model);
        PageStore.EnsureDesigns(bookFolder, PageGroupRole.Publisher, model);

        // The back cover is an image the author drops in the folder, so the dialog is given one to
        // list and the tab is checked with a page in it.
        PageStore.Ensure(bookFolder, model);
        MakeImage(Path.Combine(PagesOf(bookFolder), "backcover", "back.jpg"), Colors.DarkOliveGreen, "BACK", 600, 800);
        PageStore.Ensure(bookFolder, model);

        var dialog = new PdfPageSetupDialog(options.Clone(), bookFolder: bookFolder);
        dialog.Show();
        Pump(dialog, () => dialog.IsLoaded, 5000);
        Pump(dialog, () => FontsLoaded(dialog), 30000);
        Pump(dialog, () => false, 1200);
        Capture(dialog, Path.Combine(outputDirectory, "dialog-pdf-setup.png"));
        report.AppendLine($"dialog book folder: exists={Directory.Exists(bookFolder)} profile={File.Exists(profilePath)} resolved={BookLayout.BookProfilePath(bookFolder)} folders={(Directory.Exists(bookFolder) ? string.Join(", ", Directory.GetDirectories(bookFolder).Select(Path.GetFileName)) : "-")}");

        var tabs = FindChild<TabControl>(dialog);
        report.AppendLine($"tabs: {(tabs is null ? "MISSING" : string.Join(", ", tabs.Items.Cast<TabItem>().Select(item => item.Header)))}");

        if (tabs is not null)
        {
            report.AppendLine($"tab strip: {tabs.TabStripPlacement} selected={tabs.SelectedIndex}");

            // The profile tab comes first in the strip: it lists the profiles of the settings folder
            // and records the one the book is set up from.
            tabs.SelectedIndex = 0;
            Pump(dialog, () => false, 600);
            report.AppendLine($"profile tab: {DescribeProfileList(dialog)}");
            Capture(dialog, Path.Combine(outputDirectory, "dialog-select-profile.png"));
            report.AppendLine($"profile applied: {PressButton(dialog, "ApplyProfile_Click", null!)}");
            Pump(dialog, () => false, 800);
            report.AppendLine($"profile recorded: {ProfileStore.Current(bookFolder)} message='{FindChildByName<TextBlock>(dialog, "MessageText")?.Text}'");
            report.AppendLine($"profile tab after the apply: {DescribeProfileList(dialog)}");

            // A second profile is chosen the same way, so the report shows that the tab records the
            // one that was picked instead of the default, and the default is put back afterwards.
            var profileList = FindChildByName<ListBox>(dialog, "ProfileList");
            if (profileList is not null && profileList.Items.Count > 1)
            {
                profileList.SelectedIndex = 1;
                Pump(dialog, () => false, 400);
                report.AppendLine($"second profile: {PressButton(dialog, "ApplyProfile_Click", null!)} recorded={ProfileStore.Current(bookFolder)}");
                Capture(dialog, Path.Combine(outputDirectory, "dialog-select-profile-second.png"));

                profileList.SelectedIndex = 0;
                Pump(dialog, () => false, 400);
                report.AppendLine($"default profile again: {PressButton(dialog, "ApplyProfile_Click", null!)} recorded={ProfileStore.Current(bookFolder)}");
            }
            else
            {
                report.AppendLine($"second profile: none listed ({profileList?.Items.Count.ToString() ?? "no list"})");
            }

            tabs.SelectedIndex = 2;
            Pump(dialog, () => false, 800);
            Capture(dialog, Path.Combine(outputDirectory, "dialog-book-covers.png"));

            var frontBox = FindChildByName<TextBox>(dialog, "FrontCoverBox");
            var frontPreview = FindChildByName<Image>(dialog, "FrontCoverPreview");
            report.AppendLine($"covers tab: front={frontBox?.Text} frontPreview={Describe(frontPreview)} backCoverBox={(FindChildByName<TextBox>(dialog, "BackCoverBox") is null ? "absent" : "PRESENT")}");
            report.AppendLine($"includeCovers: {FindChildByName<CheckBox>(dialog, "IncludeCoversBox")?.IsChecked}");

            // The page lists of the tabs come from the pages of the book folder, so the report says
            // which pages each part holds and whether their files are there. A tab only builds its
            // content once it is shown, so each tab is opened in turn.
            foreach (var (index, listName) in new[]
            {
                (2, "CoverPageList"),
                (3, "BlurbPageList"),
                (4, "PublisherPageList"),
                (5, "IndexPageList"),
                (6, "ContentPageList"),
                (7, "AppendixPageList"),
                (8, "BackCoverPageList")
            })
            {
                tabs.SelectedIndex = index;
                Pump(dialog, () => false, 400);
                report.AppendLine($"page lists: {DescribePageList(dialog, listName)}");

                if (index == 8)
                {
                    Capture(dialog, Path.Combine(outputDirectory, "dialog-back-cover-pages.png"));
                }
            }

            // The index tab writes its pages from the chapters of the book. A book folder with no
            // content to index - the folder of this dialog - has no chapter to build the index from,
            // so the button says so instead of writing a page.
            tabs.SelectedIndex = 5;
            Pump(dialog, () => false, 400);
            report.AppendLine($"build index: {PressButton(dialog, "BuildIndex_Click", "Index")}");
            Pump(dialog, () => false, 600);
            report.AppendLine($"index after the build: message='{FindChildByName<TextBlock>(dialog, "MessageText")?.Text}' pages={DescribePageList(dialog, "IndexPageList")}");

            // The arrows and the insert button of a page list are driven through the handlers the
            // buttons are wired to, so the report shows the order a move leaves behind and the page an
            // insert adds, as the configuration records them.
            tabs.SelectedIndex = 4;
            Pump(dialog, () => false, 400);
            report.AppendLine($"publisher before the moves: {DescribePageList(dialog, "PublisherPageList")}");
            Capture(dialog, Path.Combine(outputDirectory, "dialog-publisher-pages.png"));
            if (FindChildByName<ListBox>(dialog, "PublisherPageList") is { } publisherList
                && publisherList.Items.Count > 0
                && publisherList.ItemContainerGenerator.ContainerFromIndex(0) is FrameworkElement firstRow)
            {
                report.AppendLine(
                    $"publisher row: list={publisherList.ActualWidth:0} row={firstRow.ActualWidth:0}"
                    + $" wanted={firstRow.DesiredSize.Width:0}");
            }

            if (PageItemOf(dialog, "PublisherPageList", "pages/publisher/title.rtf") is { } titlePage)
            {
                report.AppendLine($"arrow down: {PressButton(dialog, "MovePageDown_Click", titlePage)}");
                Pump(dialog, () => false, 300);
                report.AppendLine($"publisher after the title page moved down: {DescribePageList(dialog, "PublisherPageList")}");

                report.AppendLine($"arrow up: {PressButton(dialog, "MovePageUp_Click", titlePage)}");
                Pump(dialog, () => false, 300);
                report.AppendLine($"publisher after the title page moved back: {DescribePageList(dialog, "PublisherPageList")}");
            }

            report.AppendLine($"insert page: {PressButton(dialog, "InsertPage_Click", "Publisher")}");
            Pump(dialog, () => false, 400);
            report.AppendLine($"publisher after the insert: {DescribePageList(dialog, "PublisherPageList")}");
            report.AppendLine($"pages in the configuration: {DescribePages(bookFolder)}");

            // The delete button asks for a confirmation first, so the store call behind it is
            // exercised directly: the page has to leave the book and the file has to leave the disk.
            var inserted = Path.Combine(PagesOf(bookFolder), "publisher", "dedicate.rtf");
            PageStore.DeleteFile(bookFolder, PageGroupRole.Publisher, "pages/publisher/dedicate.rtf");
            report.AppendLine($"after the delete: file={File.Exists(inserted)} pages={DescribePages(bookFolder)}");

            // The blank page button keeps an empty sheet in the part, where the selected page is, so
            // the report shows the page it adds and the design it writes for it.
            report.AppendLine($"insert blank page: {PressButton(dialog, "InsertBlankPage_Click", "Publisher")}");
            Pump(dialog, () => false, 400);
            report.AppendLine($"publisher after the blank page: {DescribePageList(dialog, "PublisherPageList")}");

            var blank = Path.Combine(PagesOf(bookFolder), "publisher", "blank.rtf");
            report.AppendLine($"blank page: file={File.Exists(blank)} size={(File.Exists(blank) ? new FileInfo(blank).Length : 0)} pages={DescribePages(bookFolder)}");

            report.AppendLine($"insert second blank page: {PressButton(dialog, "InsertBlankPage_Click", "Publisher")}");
            Pump(dialog, () => false, 400);
            report.AppendLine($"publisher after the second blank page: {DescribePageList(dialog, "PublisherPageList")}");
            report.AppendLine($"second blank page: file={File.Exists(Path.Combine(PagesOf(bookFolder), "publisher", "blank-2.rtf"))}");

            PageStore.DeleteFile(bookFolder, PageGroupRole.Publisher, "pages/publisher/blank-2.rtf");
            PageStore.DeleteFile(bookFolder, PageGroupRole.Publisher, "pages/publisher/blank.rtf");
            report.AppendLine($"after the blank pages are taken out: pages={DescribePages(bookFolder)}");

            tabs.SelectedIndex = 2;
            Pump(dialog, () => false, 400);

            tabs.SelectedIndex = 1;
            Pump(dialog, () => false, 800);
            Capture(dialog, Path.Combine(outputDirectory, "dialog-book-model.png"));

            var bookTab = FindChildByName<TabItem>(dialog, "BookModelTab");
            var displayName = FindChildByName<TextBox>(dialog, "DisplayNameBox");
            var coverType = FindChildByName<ComboBox>(dialog, "CoverTypeBox");
            report.AppendLine($"book model tab: {bookTab?.Visibility.ToString() ?? "MISSING"} coverTypes={coverType?.Items.Count ?? 0} seed='{displayName?.Text}' year='{FindChildByName<TextBox>(dialog, "YearBox")?.Text}'");

            if (displayName is not null)
            {
                displayName.Text = "Nouka - Collected Edition";
            }

            if (FindChildByName<TextBox>(dialog, "AuthorBox") is { } authorBox)
            {
                authorBox.Text = "Harness Author";
            }

            if (FindChildByName<TextBox>(dialog, "PaperbackPriceBox") is { } paperbackBox)
            {
                paperbackBox.Text = "12.50";
            }

            if (FindChildByName<TextBox>(dialog, "HardCoverPriceBox") is { } hardCoverBox)
            {
                hardCoverBox.Text = "24.99";
            }

            if (FindChildByName<TextBox>(dialog, "IsbnBox") is { } isbnBox)
            {
                isbnBox.Text = "978-3-16-148410-0";
            }

            if (FindChildByName<TextBox>(dialog, "CopyrightBox") is { } copyrightBox)
            {
                copyrightBox.Text = "(c) 2024 Harness Press";
            }

            if (FindChildByName<TextBox>(dialog, "YearBox") is { } yearBox)
            {
                yearBox.Text = "2024";
            }

            if (coverType is not null)
            {
                coverType.SelectedIndex = 1;
            }

            // The book model is written by the same debounced save as the layout, so the values have
            // to reach config.json without a Save button being pressed.
            Pump(dialog, () => false, 1500);

            var savedBook = BookLayout.LoadBook(bookFolder);
            report.AppendLine($"book model saved: name='{savedBook?.DisplayName}' author='{savedBook?.Author}' cover={savedBook?.CoverType} paperback={savedBook?.PaperbackPrice} hardcover={savedBook?.HardCoverPrice} isbn='{savedBook?.Isbn}' year={savedBook?.YearOfProduction} copyright='{savedBook?.Copyright}'");

            var reopened = new PdfPageSetupDialog(options.Clone(), bookFolder: bookFolder);
            reopened.Show();
            Pump(reopened, () => reopened.IsLoaded, 5000);

            // The tab control only keeps the selected tab in the visual tree, so the Book Model tab
            // has to be selected before its fields can be read back.
            if (FindChild<TabControl>(reopened) is { } reopenedTabs)
            {
                reopenedTabs.SelectedIndex = 1;
                Pump(reopened, () => false, 600);
            }

            var reloadedName = FindChildByName<TextBox>(reopened, "DisplayNameBox")?.Text;
            var reloadedCover = FindChildByName<ComboBox>(reopened, "CoverTypeBox")?.SelectedItem;
            var reloadedYear = FindChildByName<TextBox>(reopened, "YearBox")?.Text;
            report.AppendLine($"book model reloaded: name='{reloadedName}' cover={reloadedCover} year='{reloadedYear}'");
            reopened.Close();
        }

        var progress = FindChildByName<TextBlock>(dialog, "ProgressText");
        var bar = FindChildByName<ProgressBar>(dialog, "ProgressBar");
        var ok = FindChildByName<Button>(dialog, "OkButton");
        report.AppendLine($"footer: progress={progress?.Visibility.ToString() ?? "?"} bar={bar?.Visibility.ToString() ?? "?"} okEnabled={ok?.IsEnabled}");
        report.AppendLine($"message: {FindChildByName<TextBlock>(dialog, "MessageText")?.Text}");

        var defaults = new PdfExportOptions();
        report.AppendLine($"default layout: {defaults.PageWidthMm} x {defaults.PageHeightMm} mm {defaults.SizeUnit}");

        // The tab control only keeps the selected tab in the visual tree, so the Print Setup tab has
        // to be selected again before its list can be inspected.
        if (tabs is not null)
        {
            tabs.SelectedIndex = 9;
            Pump(dialog, () => false, 300);
        }

        var layouts = FindChildByName<ListBox>(dialog, "PresetList");
        report.AppendLine($"layout list: {layouts?.Items.Count ?? 0} options, selected={layouts?.SelectedItem}");

        if (layouts is not null)
        {
            layouts.SelectedIndex = 0;
            layouts.ScrollIntoView(layouts.SelectedItem);
            Pump(dialog, () => false, 1200);
            var width = FindChildByName<TextBox>(dialog, "WidthBox");
            var height = FindChildByName<TextBox>(dialog, "HeightBox");
            report.AppendLine($"first layout applied: width={width?.Text} height={height?.Text} unit={FindChildByName<ComboBox>(dialog, "UnitBox")?.SelectedIndex}");
            Capture(dialog, Path.Combine(outputDirectory, "dialog-layout-selected.png"));
        }

        // The setup is written to the profile.json of the book folder as it changes, so the file has to
        // be there after a change without any Save button being pressed.
        var saved = BookLayout.LoadFromBook(bookFolder);
        report.AppendLine($"implicit save: file={File.Exists(profilePath)} width={saved?.Options.PageWidthMm} height={saved?.Options.PageHeightMm} name={saved?.Name}");
        report.AppendLine($"save controls removed: configBox={FindChildByName<ComboBox>(dialog, "ConfigBox") is not null} path='{FindChildByName<TextBlock>(dialog, "ConfigPathText")?.Text}'");

        dialog.Close();
        report.AppendLine($"implicit save on close: file={File.Exists(profilePath)}");
        report.AppendLine($"book folder after the dialog: exists={Directory.Exists(bookFolder)} profile={BookLayout.BookProfilePath(bookFolder)} folders={(Directory.Exists(bookFolder) ? string.Join(", ", Directory.GetDirectories(bookFolder).Select(Path.GetFileName)) : "-")}");

        if (Directory.Exists(bookFolder))
        {
            Directory.Delete(bookFolder, recursive: true);
        }
    }

    private static string Describe(Image? image)
        => image?.Source is BitmapSource source ? $"{source.PixelWidth}x{source.PixelHeight}" : "EMPTY";

    /// <summary>
    /// The pages a tab lists, in the order the list shows them, each with the file it is kept in and
    /// what the list says about it - for example
    /// <c>publisher: Title page[pages/publisher/title.rtf]:Designed, Dedication[pages/publisher/dedicate.rtf]:Not designed</c>.
    /// The state and the path are read off the items of the list, which the dialog keeps to itself.
    /// </summary>
    private static string DescribePageList(DependencyObject dialog, string name)
    {
        if (FindChildByName<ListBox>(dialog, name) is not { } list)
        {
            return $"{name}=MISSING";
        }

        var items = list.Items.Cast<object>().Select(item =>
        {
            var path = item.GetType().GetProperty("RelativePath")?.GetValue(item) as string;
            var state = item.GetType().GetProperty("State")?.GetValue(item) as string;
            return $"{item}[{path}]:{state}";
        });

        return $"{name}=[{string.Join(", ", items)}]";
    }

    /// <summary>
    /// The profiles the Select Profile tab lists - name, what the profile is for and whether the book
    /// follows it - together with the summary under the list, so the report says what the tab shows.
    /// </summary>
    private static string DescribeProfileList(DependencyObject dialog)
    {
        if (FindChildByName<ListBox>(dialog, "ProfileList") is not { } list)
        {
            return "ProfileList=MISSING";
        }

        var items = list.Items.Cast<object>().Select(item =>
        {
            var name = item.GetType().GetProperty("Name")?.GetValue(item) as string;
            var details = item.GetType().GetProperty("Details")?.GetValue(item) as string;
            var state = item.GetType().GetProperty("State")?.GetValue(item) as string;
            return $"{name}[{details}]{(string.IsNullOrEmpty(state) ? string.Empty : ":" + state)}";
        });

        var selected = list.SelectedItem?.GetType().GetProperty("Name")?.GetValue(list.SelectedItem) as string;

        return $"ProfileList=[{string.Join(", ", items)}] selected={selected ?? "none"}"
            + $" summary='{FindChildByName<TextBlock>(dialog, "ProfileSummaryText")?.Text?.Replace(Environment.NewLine, " | ")}'";
    }

    /// <summary>
    /// Presses a button of the dialog the way the author would, by calling the handler it is wired
    /// to with the tag the button carries, so the report covers the arrow, insert and delete paths of
    /// a page list instead of only the state the lists are built from.
    /// </summary>
    private static string PressButton(PdfPageSetupDialog dialog, string handler, object tag)
    {
        var method = typeof(PdfPageSetupDialog).GetMethod(handler, BindingFlags.Instance | BindingFlags.NonPublic);

        if (method is null)
        {
            return $"{handler}=MISSING";
        }

        method.Invoke(dialog, [new Button { Tag = tag }, new RoutedEventArgs()]);
        return $"{handler}=pressed";
    }

    /// <summary>The pages the profile of <paramref name="bookFolder"/> records, folder by folder.</summary>
    private static string DescribePages(string bookFolder) =>
        string.Join(
            " | ",
            (BookProfile.Load(bookFolder)?.Book?.Pages ?? [])
                .Select(page => $"{page.Order}:{page.FilePath} -> "
                    + string.Join(", ", (page.Paths ?? []).Select(file => $"{file.Order}:{file.FilePath}[{file.ContentType}]"))));

    /// <summary>The item of a page list that names <paramref name="relativePath"/>, as its buttons carry it.</summary>
    private static object? PageItemOf(DependencyObject dialog, string name, string relativePath) =>
        FindChildByName<ListBox>(dialog, name) is { } list
            ? list.Items.Cast<object>().FirstOrDefault(item => string.Equals(
                item.GetType().GetProperty("RelativePath")?.GetValue(item) as string,
                relativePath,
                StringComparison.OrdinalIgnoreCase))
            : null;

    private static string Describe(FrameworkElement? element, Visual ancestor)
    {
        if (element is null || element.RenderSize.IsEmpty)
        {
            return "MISSING";
        }

        var bounds = element.TransformToAncestor(ancestor).TransformBounds(new Rect(element.RenderSize));
        return $"{bounds.X:0},{bounds.Y:0} {bounds.Width:0}x{bounds.Height:0}";
    }

    private static bool FontsLoaded(PdfPageSetupDialog dialog)
    {
        var fontBox = FindChildByName<ComboBox>(dialog, "FontBox");
        return fontBox is not null && fontBox.Items.Count > 0;
    }

    private static void Pump(Window window, Func<bool> until, int timeoutMilliseconds)
    {
        var start = Environment.TickCount64;
        while (Environment.TickCount64 - start < timeoutMilliseconds)
        {
            window.Dispatcher.Invoke(() => { }, DispatcherPriority.Background);
            if (until())
            {
                return;
            }

            Thread.Sleep(30);
        }
    }

    private static void Capture(Window window, string path)
    {
        window.UpdateLayout();
        var width = (int)Math.Ceiling(window.ActualWidth);
        var height = (int)Math.Ceiling(window.ActualHeight);
        var bitmap = new RenderTargetBitmap(Math.Max(width, 1), Math.Max(height, 1), 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(window);

        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var stream = File.Create(path);
        encoder.Save(stream);
    }

    private static void MakeImage(string path, Color color, string text, int width, int height)
    {
        MakeImage(path, color, text, width, height, banded: false);
    }

    /// <summary>
    /// Draws a test image with a red strip down its left and right edges, so a crop to the page
    /// shape can be told apart from a letterbox and from a stretch.
    /// </summary>
    private static void MakeBandedImage(string path, Color color, string text, int width, int height)
    {
        MakeImage(path, color, text, width, height, banded: true);
    }

    private static void MakeImage(string path, Color color, string text, int width, int height, bool banded)
    {
        var visual = new DrawingVisual();
        using (var context = visual.RenderOpen())
        {
            context.DrawRectangle(new SolidColorBrush(color), null, new Rect(0, 0, width, height));
            context.DrawRectangle(Brushes.White, null, new Rect(width * 0.1, height * 0.4, width * 0.8, 4));

            if (banded)
            {
                // Narrower than the strip the crop removes from each side, so a real crop leaves
                // none of it on the page while a stretch would squeeze it back into view.
                var strip = width * 0.015;
                context.DrawRectangle(Brushes.Red, null, new Rect(0, 0, strip, height));
                context.DrawRectangle(Brushes.Red, null, new Rect(width - strip, 0, strip, height));
            }

            var formatted = new FormattedText(
                text,
                CultureInfo.InvariantCulture,
                FlowDirection.LeftToRight,
                new Typeface("Segoe UI"),
                width / 10.0,
                Brushes.White,
                96);
            context.DrawText(formatted, new Point((width - formatted.Width) / 2, height * 0.45));
        }

        var bitmap = new RenderTargetBitmap(width, height, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(visual);

        BitmapEncoder encoder;
        BitmapSource pixels = bitmap;
        if (IsJpeg(path))
        {
            encoder = new JpegBitmapEncoder { QualityLevel = 92 };
            pixels = new FormatConvertedBitmap(bitmap, PixelFormats.Bgr24, null, 0);
        }
        else
        {
            encoder = new PngBitmapEncoder();
        }

        encoder.Frames.Add(BitmapFrame.Create(pixels));
        using var stream = File.Create(path);
        encoder.Save(stream);
    }

    private static bool IsJpeg(string path) => Path.GetExtension(path).ToLowerInvariant() switch
    {
        ".jpg" or ".jpeg" => true,
        _ => false
    };

    /// <summary>
    /// Draws the centring test image: a cross through the middle of the sheet and a coloured square
    /// in each corner, so the trim of a full bleed cover can be measured.
    /// </summary>
    private static void MakeCentringImage(string path, int width, int height)
    {
        const int Bar = 6;
        const int Square = 40;

        var visual = new DrawingVisual();
        using (var context = visual.RenderOpen())
        {
            context.DrawRectangle(Brushes.White, null, new Rect(0, 0, width, height));
            context.DrawRectangle(Brushes.Black, null, new Rect((width - Bar) / 2.0, 0, Bar, height));
            context.DrawRectangle(Brushes.Black, null, new Rect(0, (height - Bar) / 2.0, width, Bar));
            context.DrawRectangle(Brushes.Red, null, new Rect(0, 0, Square, Square));
            context.DrawRectangle(Brushes.Green, null, new Rect(width - Square, 0, Square, Square));
            context.DrawRectangle(Brushes.Blue, null, new Rect(0, height - Square, Square, Square));
            context.DrawRectangle(Brushes.Yellow, null, new Rect(width - Square, height - Square, Square, Square));
        }

        var bitmap = new RenderTargetBitmap(width, height, 96, 96, PixelFormats.Pbgra32);
        bitmap.Render(visual);

        var encoder = new PngBitmapEncoder();
        encoder.Frames.Add(BitmapFrame.Create(bitmap));
        using var stream = File.Create(path);
        encoder.Save(stream);
    }

    private static T? FindChild<T>(DependencyObject parent) where T : DependencyObject
    {
        for (var index = 0; index < VisualTreeHelper.GetChildrenCount(parent); index++)
        {
            var child = VisualTreeHelper.GetChild(parent, index);
            if (child is T match)
            {
                return match;
            }

            var nested = FindChild<T>(child);
            if (nested is not null)
            {
                return nested;
            }
        }

        return null;
    }

    private static T? FindChildByName<T>(DependencyObject parent, string name) where T : FrameworkElement
    {
        for (var index = 0; index < VisualTreeHelper.GetChildrenCount(parent); index++)
        {
            var child = VisualTreeHelper.GetChild(parent, index);
            if (child is T match && match.Name == name)
            {
                return match;
            }

            var nested = FindChildByName<T>(child, name);
            if (nested is not null)
            {
                return nested;
            }
        }

        return null;
    }
}
