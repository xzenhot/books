using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Documents;
using System.Windows.Media;

using WriterWorker.Ctl;
using WriterWorker.Models;
using WriterWorker.Views;

namespace WriterWorker.Configuration;

/// <summary>
/// Builds the index of a book from its chapters: the title of every chapter with the titles of the
/// segments that print under it, two blank lines between one chapter and the next. Nothing fixes
/// how many pages the index takes - the entries are packed into pages of the text area of the page
/// setup, so a book that grows gains index pages and a book that shrinks loses the ones it no
/// longer needs. Each page is written as an RTF design in the index folder of the book, so the
/// pages can be opened and edited like any other page of the book.
/// </summary>
internal static class IndexPages
{
    /// <summary>Size the title of a chapter is set in, in DIP.</summary>
    private const double ChapterSize = 15;

    /// <summary>Size the title of a segment is set in, in DIP.</summary>
    private const double SegmentSize = 12;

    /// <summary>How far a segment title is indented under its chapter title, in DIP.</summary>
    private const double SegmentIndent = 18;

    private const double ChapterSpaceBefore = 10;
    private const double ChapterSpaceAfter = 2;
    private const double SegmentSpaceAfter = 1;

    /// <summary>Height of a line as a multiple of its size, kept the same on the page.</summary>
    private const double LineHeight = 1.3;

    /// <summary>
    /// Share of the text area the pages are filled to. A line that wraps in the export but not in
    /// the measure would push an entry onto the next page, which is what the headroom is for.
    /// </summary>
    private const double Headroom = 0.96;

    private const double MillimetresPerPoint = 25.4 / 72.0;

    /// <summary>Size the export lays a design out at: the size of the body text of a page.</summary>
    private static double DocumentSize => MarkdownFlow.DefaultFontSize * PdfExport.DipToPoint;

    /// <summary>
    /// Writes the index pages of <paramref name="bookFolder"/> from <paramref name="chapters"/>,
    /// following the page setup in <paramref name="options"/>, and records them as the pages of the
    /// index part of the book. Returns the paths of the pages it wrote, relative to the book folder.
    /// A book with no chapter writes no page and keeps none, so the export falls back to the pages
    /// it reserves for the index.
    /// </summary>
    public static IReadOnlyList<string> Write(
        string bookFolder,
        IReadOnlyList<Chapter> chapters,
        PdfExportOptions options)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(bookFolder);
        ArgumentNullException.ThrowIfNull(chapters);
        ArgumentNullException.ThrowIfNull(options);

        var folder = Path.GetFullPath(bookFolder);
        var relativeFolder = PageStore.GroupOf(folder, PageGroupRole.Index)?.FilePath
            ?? BookPages.FolderPathOf(PageGroupRole.Index);

        if (!relativeFolder.EndsWith('/'))
        {
            relativeFolder += "/";
        }

        var pagesFolder = BookProfile.ProfileFolderOf(folder);
        var sheet = SheetOf(options);
        var pages = Paginate(EntriesOf(chapters), sheet);
        var written = new List<string>();

        for (var index = 0; index < pages.Count; index++)
        {
            var relativePath = relativeFolder + NameOf(index) + BookPages.RtfExtension;
            var path = BookPages.Resolve(pagesFolder, relativePath)
                ?? throw new InvalidOperationException($"The index page '{relativePath}' has no path.");

            RtfExport.Save(DocumentOf(pages[index], options.FontFamily), path);
            written.Add(relativePath);
        }

        DeleteStale(pagesFolder, relativeFolder, written);
        PageStore.ReplaceFiles(folder, PageGroupRole.Index, written);

        return written;
    }

    /// <summary>Name of the <paramref name="index"/>th page of the index: <c>index</c>, <c>index-2</c>, and so on.</summary>
    private static string NameOf(int index) =>
        (index == 0 ? "index" : "index-" + (index + 1).ToString(CultureInfo.InvariantCulture));

    /// <summary>
    /// Drops the index pages an earlier build wrote that the book no longer fills, so a book that
    /// loses chapters does not keep printing the pages of the index it used to have. Only the names
    /// this builder gives its own pages are touched; a design the author added to the folder under
    /// another name is left alone.
    /// </summary>
    private static void DeleteStale(string pagesFolder, string relativeFolder, IReadOnlyList<string> written)
    {
        var folder = BookPages.Resolve(pagesFolder, relativeFolder);
        if (folder is null || !Directory.Exists(folder))
        {
            return;
        }

        for (var index = written.Count; ; index++)
        {
            var path = BookPages.Resolve(folder, NameOf(index) + BookPages.RtfExtension);
            if (path is null || !File.Exists(path))
            {
                return;
            }

            File.Delete(path);
        }
    }

    /// <summary>
    /// The lines of the index in the order they print: the title of a chapter, then the titles of
    /// the segments that print under it, then two blank lines before the next chapter.
    /// </summary>
    private static List<Entry> EntriesOf(IReadOnlyList<Chapter> chapters)
    {
        var entries = new List<Entry>();

        foreach (var chapter in chapters)
        {
            var title = ChapterTitle(chapter);

            if (entries.Count > 0)
            {
                // Two blank lines keep the last segment of a chapter off the title of the next one.
                entries.Add(Entry.Blank);
                entries.Add(Entry.Blank);
            }

            entries.Add(new Entry(title, ChapterSize, true, 0, ChapterSpaceBefore, ChapterSpaceAfter));

            foreach (var segment in chapter.Segments)
            {
                // A segment without a body prints no page, so it has no line in the index either.
                if (string.IsNullOrWhiteSpace(segment.Body))
                {
                    continue;
                }

                entries.Add(new Entry(SegmentTitle(segment), SegmentSize, false, SegmentIndent, 0, SegmentSpaceAfter));
            }
        }

        return entries;
    }

    /// <summary>
    /// Packs <paramref name="entries"/> into pages that fit <paramref name="sheet"/>. A page always
    /// takes the entry it starts on, so an entry too tall for a page of its own still prints, and the
    /// blank lines that open a chapter are dropped when a page breaks between them and its title.
    /// </summary>
    private static List<List<Entry>> Paginate(IReadOnlyList<Entry> entries, Sheet sheet)
    {
        var pages = new List<List<Entry>>();
        var page = new List<Entry>();
        var used = 0.0;

        foreach (var entry in entries)
        {
            var height = sheet.HeightOf(entry);

            if (page.Count > 0 && used + height > sheet.Height)
            {
                pages.Add(page);
                page = [];
                used = 0;
            }

            if (page.Count == 0 && entry.Text.Length == 0)
            {
                // A page never opens with a blank line: the break already made the gap.
                continue;
            }

            page.Add(entry);
            used += height;
        }

        if (page.Count > 0)
        {
            pages.Add(page);
        }

        return pages;
    }

    /// <summary>The pages as the export prints them: every entry a paragraph, a blank entry an empty one.</summary>
    private static FlowDocument DocumentOf(IReadOnlyList<Entry> page, string? family)
    {
        var document = new FlowDocument
        {
            FontFamily = new FontFamily(
                string.IsNullOrWhiteSpace(family) ? PdfExport.DefaultFontFamily : family),
            FontSize = MarkdownFlow.DefaultFontSize,
            PagePadding = new Thickness(0)
        };

        foreach (var entry in page)
        {
            // A blank line is set in the body size of the page, the size the export prints an empty
            // paragraph at, so the gap it leaves matches the one the pages were measured with.
            var size = entry.Size > 0 ? entry.Size : MarkdownFlow.DefaultFontSize;

            var paragraph = new Paragraph
            {
                Margin = new Thickness(entry.Indent, entry.SpaceBefore, 0, entry.SpaceAfter),
                FontSize = size,
                LineHeight = size * LineHeight
            };

            if (entry.Text.Length > 0)
            {
                paragraph.Inlines.Add(new Run(entry.Text)
                {
                    FontSize = entry.Size,
                    FontWeight = entry.Bold ? FontWeights.Bold : FontWeights.Normal
                });
            }

            document.Blocks.Add(paragraph);
        }

        return document;
    }

    private static string ChapterTitle(Chapter chapter) =>
        FirstText(chapter.Title, chapter.Name) is { Length: > 0 } title
            ? title
            : chapter.Index > 0 ? $"Chapter {chapter.Index}" : string.Empty;

    private static string SegmentTitle(Segment segment) =>
        FirstText(segment.Title) is { Length: > 0 } title
            ? title
            : segment.Index > 0 ? $"Segment {segment.Index}" : string.Empty;

    private static string FirstText(params string?[] values) =>
        values.Select(value => value?.Trim()).FirstOrDefault(value => !string.IsNullOrEmpty(value)) ?? string.Empty;

    /// <summary>The text area of a page of <paramref name="options"/>, in the units the index is measured in.</summary>
    private static Sheet SheetOf(PdfExportOptions options)
    {
        var width = Math.Max(1, options.PageWidthMm - (2 * options.MarginMm));
        var height = Math.Max(1, options.PageHeightMm - (2 * options.MarginMm));
        var baseSize = options.FontSize is > 0 ? options.FontSize.Value : DocumentSize;

        return new Sheet(
            width / MillimetresPerPoint,
            (height / MillimetresPerPoint) * Headroom,
            DocumentSize > 0 ? baseSize / DocumentSize : 1,
            baseSize,
            options.FontFamily);
    }

    /// <summary>A line of the index, and how it is set on the page.</summary>
    private readonly record struct Entry(
        string Text,
        double Size,
        bool Bold,
        double Indent,
        double SpaceBefore,
        double SpaceAfter)
    {
        /// <summary>A line with nothing on it, printed as a line of body text.</summary>
        public static Entry Blank => new(string.Empty, 0, false, 0, 0, 0);
    }

    /// <summary>
    /// The text area of a page as the export fills it, and how tall a line of the index comes out
    /// there: the export prints a design at the body size of the page, so a size of the index is
    /// scaled the same way a heading of the book is, while the space around it is not.
    /// </summary>
    private sealed record Sheet(double Width, double Height, double Scale, double BaseSize, string? Family)
    {
        public double HeightOf(Entry entry)
        {
            var spacing = (entry.SpaceBefore + entry.SpaceAfter) * PdfExport.DipToPoint;

            if (entry.Text.Length == 0)
            {
                return spacing + LineOf(Measure("Ag", BaseSize / PdfExport.DipToPoint, bold: false));
            }

            var text = Measure(entry.Text, entry.Size * Scale, entry.Bold);
            var available = (Width - (entry.Indent * PdfExport.DipToPoint)) / PdfExport.DipToPoint;
            var lines = available <= 0
                ? 1
                : Math.Max(1, (int)Math.Ceiling(text.WidthIncludingTrailingWhitespace / available));

            return spacing + (lines * LineOf(text));
        }

        /// <summary>
        /// Height of a printed line in points. A line is taller than the size it is set in - the font
        /// adds its own leading - and the page sets the line height on top of that, so the height the
        /// measure lays a line out at is taken from the font rather than assumed from the size.
        /// </summary>
        private static double LineOf(FormattedText text) =>
            text.Height * PdfExport.DipToPoint * LineHeight;

        private FormattedText Measure(string text, double size, bool bold) =>
            new(
                text,
                CultureInfo.CurrentUICulture,
                FlowDirection.LeftToRight,
                new Typeface(
                    new FontFamily(string.IsNullOrWhiteSpace(Family) ? PdfExport.DefaultFontFamily : Family),
                    FontStyles.Normal,
                    bold ? FontWeights.Bold : FontWeights.Normal,
                    FontStretches.Normal),
                size,
                Brushes.Black,
                1.0)
            {
                MaxTextWidth = 1e6
            };
    }
}
