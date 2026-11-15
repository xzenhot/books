using System.IO;
using System.Linq;

using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Parser.PipelineParser.Contents
{
    /// <summary>
    /// One book folder inside a pipeline root (for example <c>...\workspaces\pipeline\nouka</c>)
    /// together with the <c>book.json</c> plan read from it.
    /// </summary>
    internal sealed class BookEntry
    {
        public BookEntry(string folderPath)
        {
            FolderPath = Path.GetFullPath(folderPath);
            FolderName = Path.GetFileName(FolderPath.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
            if (string.IsNullOrEmpty(FolderName))
            {
                FolderName = FolderPath;
            }
        }

        public string FolderPath { get; }

        public string FolderName { get; }

        /// <summary>The plan read from <c>book.json</c>; null when the folder has no readable plan.</summary>
        public BookModel? Plan { get; set; }

        /// <summary>Why the plan could not be read, or null when it was.</summary>
        public string? Error { get; set; }

        /// <summary>Chapter folders found on disk, used when the plan does not state a count.</summary>
        public int ChapterFolderCount { get; set; }

        public int SegmentFolderCount { get; set; }

        public bool HasPlan => Plan is not null;

        public string DisplayName =>
            new[] { Plan?.BookLongTitle, Plan?.BookName, FolderName }
                .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? FolderName;

        public string? Language => Plan?.Language;

        public string? Form => Plan?.Form;

        public string? Gist => Plan?.Gist;

        public int ChapterCount => Plan is { ChapterCount: > 0 } plan ? plan.ChapterCount : ChapterFolderCount;

        public int? SegmentCount => Plan is { SegmentCount: > 0 } plan ? plan.SegmentCount : null;

        public string PlanState => Plan is not null ? "loaded" : Error is null ? "missing" : "invalid";

        public override string ToString() => DisplayName;
    }
}
