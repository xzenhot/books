using System;
using System.Globalization;
using System.Linq;

using WriterWorker.Controller;
using WriterWorker.Parser.PipelineParser.Contents;
using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Models
{
    /// <summary>
    /// Reads a workspace book folder into <see cref="Book"/>: this is the pipeline parser, and the
    /// converter every other parser reuses. Every decision about which file wins is made here, so
    /// the pages and the renderer only ever see resolved text and stay free of folder knowledge.
    /// </summary>
    public sealed class ConfigToModel : IBookParser
    {
        /// <summary>Parser for books of the writer pipeline; it holds no state, so one is shared.</summary>
        public static ConfigToModel Instance { get; } = new();

        private ConfigToModel()
        {
        }

        public BookSource Source => BookSource.Pipeline;

        /// <summary>A book folder below a <c>pipeline</c> folder, for example <c>...\pipeline\nouka</c>.</summary>
        public bool CanParse(string? folder) => BookLibrary.IsPipelineBook(folder);

        public string? Resolve(string folder) => BookLibrary.IsBookFolder(folder) ? folder : null;

        /// <summary>Reads the plan, the progress report and every chapter and segment text of the book.</summary>
        public Book Parse(string folder) => FromConfigurationParser(BookContent.Load(folder));

        /// <summary>
        /// Projects a parsed workspace onto the render model. A segment takes the same text the book
        /// design page shows (<see cref="SegmentContent.DisplayText"/>), so the PDF and the preview
        /// cannot drift apart, and chapters and segments keep the order the parser found them in.
        /// The stage chosen for the book is handed down to every segment.
        /// </summary>
        internal static Book FromConfigurationParser(BookContent content, BookSource source = BookSource.Pipeline)
        {
            ArgumentNullException.ThrowIfNull(content);

            var stage = ContentSource.FolderName(ContentSource.Selected);

            var book = new Book
            {
                Name = content.BookName,
                Title = content.Title ?? content.BookName,
                // Published editions identify the version folder they were read from.
                Version = content.Progress?.PublishedVersion?.ToString(CultureInfo.InvariantCulture),
                Author = content.CreatedBy,
                Language = content.Language,
                Form = content.Form,
                CreatedOn = content.CreatedOn,
                WordCount = content.TotalWordCount,
                CompletedChapterCount = content.CompletedChapterCount,
                Stage = stage,
                FolderPath = content.WorkspacePath,
                Source = source,
                Gist = content.Plan?.Gist,
            };

            foreach (var document in content.Documents)
            {
                book.Documents[document.Key] = document.Value;
            }

            foreach (var chapter in content.Chapters.OrderBy(chapter => chapter.Index))
            {
                book.Chapters.Add(FromConfigurationParser(chapter, stage));
            }

            if (book.WordCount <= 0)
            {
                book.WordCount = book.Chapters.Sum(chapter => chapter.WordCount ?? 0);
            }

            return book;
        }

        internal static Chapter FromConfigurationParser(ChapterContent content, string? stage = null)
        {
            ArgumentNullException.ThrowIfNull(content);

            var chapter = new Chapter
            {
                Index = content.Index,
                Name = content.Name,
                Title = content.Title,
                Body = content.Text,
                WordCount = content.WordCount,
                WordTarget = content.WordTarget,
                State = content.State,
                Status = content.Status,
                Summary = content.Summary,
                CompletedDate = content.CompletedDate,
                CreatedBy = content.CreatedBy,
                CreatedOn = content.CreatedOn,
                FolderPath = content.Directory,
                Context = content.Context,
                Draft = content.Draft,
            };

            foreach (var reference in content.FurtherReferences)
            {
                chapter.FurtherReferences.Add(FromConfigurationParser(reference));
            }

            foreach (var segment in content.Segments.OrderBy(segment => segment.Index))
            {
                chapter.Segments.Add(FromConfigurationParser(segment, stage));
            }

            if (chapter.WordCount is not > 0)
            {
                chapter.WordCount = chapter.Segments.Sum(segment => segment.WordCount ?? 0);
            }

            return chapter;
        }

        internal static Segment FromConfigurationParser(SegmentContent content, string? stage = null)
        {
            ArgumentNullException.ThrowIfNull(content);

            var body = content.DisplayText;

            var segment = new Segment
            {
                Index = content.Index,
                Name = content.Name,
                Title = content.Title,
                Body = body,
                WordCount = content.WordCount > 0 ? content.WordCount : CountWords(body),
                Stage = stage ?? (content.DisplayTextSource is "none" ? null : content.DisplayTextSource),
                Version = LatestVersion(content),
                WordTarget = content.WordTarget,
                State = content.State,
                Summary = content.Summary,
                CreatedBy = content.CreatedBy,
                CreatedOn = content.CreatedOn,
                FolderPath = content.Directory,
                TextSource = content.TextSource,
                LatestText = content.LatestText,
                WriterText = content.WriterText,
                EditorText = content.EditorText,
                TranslatedText = content.TranslatedText,
            };

            foreach (var version in content.EditorVersions)
            {
                segment.EditorVersions.Add(FromConfigurationParser(version));
            }

            foreach (var version in content.Versions)
            {
                segment.Versions.Add(FromConfigurationParser(version));
            }

            foreach (var reference in content.FurtherReferences)
            {
                segment.FurtherReferences.Add(FromConfigurationParser(reference));
            }

            return segment;
        }

        internal static BookReference FromConfigurationParser(FurtherReferenceModel content)
        {
            ArgumentNullException.ThrowIfNull(content);

            return new BookReference
            {
                Number = content.No,
                Text = content.Reference,
                WebLink = content.WebLink,
            };
        }

        internal static SegmentVersion FromConfigurationParser(Parser.PipelineParser.Contents.SegmentVersion content)
        {
            ArgumentNullException.ThrowIfNull(content);

            return new SegmentVersion
            {
                Version = content.Version,
                Text = content.Text,
            };
        }

        /// <summary>Words of the text the model carries, used when the workspace did not count it.</summary>
        private static int CountWords(string? text) =>
            string.IsNullOrWhiteSpace(text)
                ? 0
                : text.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).Length;

        /// <summary>Highest saved snapshot number, so the render model can name where the text came from.</summary>
        private static string? LatestVersion(SegmentContent content)
        {
            var version = content.Versions.LastOrDefault()?.Version
                ?? content.EditorVersions.LastOrDefault()?.Version;

            return version > 0 ? version.Value.ToString(CultureInfo.InvariantCulture) : null;
        }
    }
}
