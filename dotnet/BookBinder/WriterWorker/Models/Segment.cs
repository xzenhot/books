using System.Collections.Generic;

namespace WriterWorker.Models
{
    /// <summary>
    /// One segment of a chapter: the text that is printed on its own page under an optional title.
    /// </summary>
    public class Segment
    {
        public string? ID { get; set; }

        /// <summary>Position in the chapter, used for the "Segment {n}" title when none is set.</summary>
        public int Index { get; set; }

        public string? Name { get; set; }
        public string? Title { get; set; }
        public string? Body { get; set; }

        /// <summary>Words in the segment text.</summary>
        public int? WordCount { get; set; }

        /// <summary>Words the plan asks for, zero when it states none.</summary>
        public int WordTarget { get; set; }

        /// <summary>Pipeline state from the segment metadata (enriched, written, edited, ...).</summary>
        public string? State { get; set; }

        public string? Summary { get; set; }

        /// <summary>Author inherited from the book plan.</summary>
        public string? CreatedBy { get; set; }

        /// <summary>Segment folder creation time, or the parent chapter completion date.</summary>
        public string? CreatedOn { get; set; }

        /// <summary>Folder the segment was read from.</summary>
        public string? FolderPath { get; set; }

        /// <summary>Folder that supplied <see cref="Body"/>: latest, editor, writer, translator or version.</summary>
        public string? TextSource { get; set; }

        /// <summary>Newest pipeline output.</summary>
        public string? LatestText { get; set; }

        /// <summary>Writer output.</summary>
        public string? WriterText { get; set; }

        /// <summary>Editor output.</summary>
        public string? EditorText { get; set; }

        /// <summary>Translator output.</summary>
        public string? TranslatedText { get; set; }

        /// <summary>Editor snapshots, oldest first.</summary>
        public List<SegmentVersion> EditorVersions { get; set; } = new List<SegmentVersion>();

        /// <summary>Saved snapshots, oldest first.</summary>
        public List<SegmentVersion> Versions { get; set; } = new List<SegmentVersion>();

        public List<BookReference> FurtherReferences { get; set; } = new List<BookReference>();

        /// <summary>Title shown in lists; falls back to the name or the index so a row is never blank.</summary>
        public string DisplayTitle =>
            !string.IsNullOrWhiteSpace(Title) ? Title!
            : !string.IsNullOrWhiteSpace(Name) ? Name!
            : $"Segment {Index}";

        public string? ImageUrl { get; set; }

        /// <summary>Highest saved snapshot of the segment, for example "3"; null when none exist.</summary>
        public string? Version { get; set; }

        /// <summary>Folder that supplied <see cref="Body"/>: latest, editor, writer or translated.</summary>
        public string? Stage { get; set; }
    }
}
