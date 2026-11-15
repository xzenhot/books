using System;
using System.Collections.Generic;
using System.Linq;

namespace WriterWorker.Models
{
    /// <summary>
    /// A book as the PDF export renders it: a title and the chapters in reading order. This is the
    /// only shape the renderer knows, so the export never depends on where the text came from.
    /// </summary>
    public class Book
    {
        public string? ID { get; set; }
        public string? Name { get; set; }
        public string? Version { get; set; }

        /// <summary>
        /// Stage the book is read at - latest, editor, translator or writer - cascaded to every
        /// segment, so the whole book renders from one pipeline folder.
        /// </summary>
        public string? Stage { get; set; }

        /// <summary>Title printed in the document metadata and offered as the file name.</summary>
        public string? Title { get; set; }

        public string? Author { get; set; }

        /// <summary>Plan language, shown in the header subtitle.</summary>
        public string? Language { get; set; }

        /// <summary>Plan form (prose, verse, ...), shown in the header subtitle.</summary>
        public string? Form { get; set; }

        /// <summary>Creation date from the plan, falling back to the folder time when shown.</summary>
        public string? CreatedOn { get; set; }

        /// <summary>Words in the book according to the plan and progress files.</summary>
        public int WordCount { get; set; }

        /// <summary>Chapters the progress report marks as completed.</summary>
        public int CompletedChapterCount { get; set; }

        /// <summary>Chapters in reading order; the count is always the number the model holds.</summary>
        public int ChapterCount => Chapters.Count;

        /// <summary>Segments of every chapter, used by the headers and the book list.</summary>
        public int SegmentCount => Chapters.Sum(chapter => chapter.Segments.Count);

        /// <summary>Folder the book was read from: a workspace book folder or a published version.</summary>
        public string? FolderPath { get; set; }

        /// <summary>Tree the book was read from.</summary>
        public BookSource Source { get; set; } = BookSource.Pipeline;

        /// <summary>One-line description of the book from the plan.</summary>
        public string? Gist { get; set; }

        /// <summary>Book level markdown keyed by file name without extension (gist, storyline, style, ...).</summary>
        public Dictionary<string, string> Documents { get; set; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        /// <summary>Why the book could not be read, or null when it was.</summary>
        public string? Error { get; set; }

        public string? CoverImageUrl { get; set; }
        public string? BackImageUrl { get; set; }

        public List<Chapter> Chapters { get; set; } = new List<Chapter>();
    }
}
