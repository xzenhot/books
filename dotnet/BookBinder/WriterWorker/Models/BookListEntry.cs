using System.Collections.Generic;

namespace WriterWorker.Models
{
    /// <summary>
    /// One row of the book list: a book folder and what the parser found in it, without the text.
    /// The list page binds this type, so it never sees the workspace files the row was built from.
    /// </summary>
    public class BookListEntry
    {
        public string FolderPath { get; set; } = string.Empty;

        public string FolderName { get; set; } = string.Empty;

        /// <summary>Title from the plan, falling back to the folder name.</summary>
        public string DisplayName { get; set; } = string.Empty;

        public string? Title { get; set; }

        public string? Language { get; set; }

        public string? Form { get; set; }

        /// <summary>One-line description of the book from the plan.</summary>
        public string? Gist { get; set; }

        /// <summary>Chapters the plan states, falling back to the chapter folders on disk.</summary>
        public int ChapterCount { get; set; }

        public int? SegmentCount { get; set; }

        /// <summary>loaded, missing or invalid - why the row has no plan.</summary>
        public string PlanState { get; set; } = "missing";

        /// <summary>Why the plan could not be read, or null when it was.</summary>
        public string? Error { get; set; }

        public BookSource Source { get; set; } = BookSource.Pipeline;

        public override string ToString() => DisplayName;
    }
}
