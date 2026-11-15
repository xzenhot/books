namespace WriterWorker.Models
{
    /// <summary>
    /// One row of the published list: a book folder together with one of its version folders.
    /// A version never changes once it appears, so every row can be opened on its own.
    /// </summary>
    public class PublishedListEntry
    {
        /// <summary>Version folder the row opens, for example <c>...\published\nouka\version6</c>.</summary>
        public string FolderPath { get; set; } = string.Empty;

        /// <summary>Book folder name, for example <c>nouka</c>.</summary>
        public string BookName { get; set; } = string.Empty;

        /// <summary>Title read from the <c>book.md</c> heading of the newest version.</summary>
        public string? Title { get; set; }

        /// <summary>Version label, for example <c>version6</c>.</summary>
        public string VersionText { get; set; } = string.Empty;

        /// <summary>Publication timestamp from <c>manifest.json</c>.</summary>
        public string? PublishedAt { get; set; }

        public int ChapterCount { get; set; }

        /// <summary>True for the newest version of the book.</summary>
        public bool IsLatest { get; set; }

        /// <summary>Why the book folder could not be read, or null when it was.</summary>
        public string? Error { get; set; }

        public BookSource Source { get; set; } = BookSource.Published;

        public string DisplayName =>
            string.IsNullOrWhiteSpace(VersionText) ? BookName : $"{BookName} · {VersionText}";

        public override string ToString() => DisplayName;
    }
}
