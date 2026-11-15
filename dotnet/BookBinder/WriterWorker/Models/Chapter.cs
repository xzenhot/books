using System;
using System.Collections.Generic;

namespace WriterWorker.Models
{
    /// <summary>
    /// One chapter of a book: a title page and the segments that follow it. The renderer needs the
    /// title, the position in the book and the text, nothing else.
    /// </summary>
    public class Chapter
    {
        public string? ID { get; set; }

        /// <summary>Position in the book, used for the "Chapter {n}" title when no title is set.</summary>
        public int Index { get; set; }

        public string? Name { get; set; }
        public string? Title { get; set; }

        /// <summary>Chapter text, printed only when no segment of the chapter carries text.</summary>
        public string? Body { get; set; }

        /// <summary>Words in the chapter according to the workspace files.</summary>
        public int? WordCount { get; set; }

        /// <summary>Words the plan asks for, zero when it states none.</summary>
        public int WordTarget { get; set; }

        /// <summary>Pipeline state from the chapter metadata (enriched, drafted, completed, ...).</summary>
        public string? State { get; set; }

        /// <summary>Status from the progress report (validated, completed, pending, ...).</summary>
        public string? Status { get; set; }

        public string? Summary { get; set; }

        public string? CompletedDate { get; set; }

        /// <summary>Author inherited from the book plan.</summary>
        public string? CreatedBy { get; set; }

        /// <summary>Chapter completion date, or the chapter folder creation time.</summary>
        public string? CreatedOn { get; set; }

        /// <summary>Folder the chapter was read from; null for a plan that has no chapter folders.</summary>
        public string? FolderPath { get; set; }

        /// <summary>Chapter context notes.</summary>
        public string? Context { get; set; }

        /// <summary>Pre-filter draft produced by the quality pass.</summary>
        public string? Draft { get; set; }

        /// <summary>True when the chapter metadata or the progress report marks the chapter as done.</summary>
        public bool IsCompleted =>
            string.Equals(State, "completed", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Status, "completed", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Status, "validated", StringComparison.OrdinalIgnoreCase);

        /// <summary>Title shown in lists; falls back to the name or the index so a row is never blank.</summary>
        public string DisplayTitle =>
            !string.IsNullOrWhiteSpace(Title) ? Title!
            : !string.IsNullOrWhiteSpace(Name) ? Name!
            : $"Chapter {Index}";

        public List<BookReference> FurtherReferences { get; set; } = new List<BookReference>();

        public string? ImageUrl { get; set; }

        public List<Segment> Segments { get; set; } = new List<Segment>();
    }
}
