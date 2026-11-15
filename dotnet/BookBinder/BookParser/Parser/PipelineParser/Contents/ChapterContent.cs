using System;
using System.Collections.Generic;
using System.Linq;

using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Parser.PipelineParser.Contents
{
    /// <summary>
    /// One chapter folder (<c>chapters/{n}</c>): metadata from chapter.json plus the
    /// assembled chapter.md, the per-filter draft and all segment texts.
    /// </summary>
    public sealed class ChapterContent
    {
        /// <summary>Numeric chapter index; label chapters such as "Introduction" carry the index from chapter.json.</summary>
        public int Index { get; set; }

        /// <summary>Folder name, for example "1" or "Introduction".</summary>
        public string Name { get; set; } = string.Empty;

        public string? Title { get; set; }

        public string? Summary { get; set; }

        /// <summary>Pipeline state from chapter.json (enriched, drafted, completed, ...).</summary>
        public string? State { get; set; }

        /// <summary>Chapter status from progress.json (validated, completed, pending, ...).</summary>
        public string? Status { get; set; }

        public string? CompletedDate { get; set; }

        /// <summary>Author inherited from the book plan.</summary>
        public string? CreatedBy { get; set; }

        /// <summary>Chapter completion date from progress.json, or the chapter folder creation time.</summary>
        public string? CreatedOn { get; set; }

        public string? FilePath { get; set; }

        public int WordTarget { get; set; }

        public int WordCount { get; set; }

        /// <summary>Assembled chapter markdown (<c>chapter.md</c>).</summary>
        public string? Markdown { get; set; }

        /// <summary>Chapter context notes (<c>context.md</c>).</summary>
        public string? Context { get; set; }

        /// <summary>Pre-filter draft produced by the quality pass (<c>filters/quality/{n}/draft.md</c>).</summary>
        public string? Draft { get; set; }

        public List<FurtherReferenceModel> FurtherReferences { get; } = new List<FurtherReferenceModel>();

        public List<SegmentContent> Segments { get; } = new List<SegmentContent>();

        public string? Directory { get; set; }

        public bool IsCompleted =>
            string.Equals(State, "completed", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Status, "completed", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Status, "validated", StringComparison.OrdinalIgnoreCase);

        /// <summary>Assembled markdown, or the segments stitched together when chapter.md is absent.</summary>
        public string? Text => Markdown ?? StitchSegments();

        public SegmentContent? GetSegment(int index) => Segments.FirstOrDefault(segment => segment.Index == index);

        private string? StitchSegments()
        {
            var texts = Segments.Select(segment => segment.Text).Where(text => !string.IsNullOrWhiteSpace(text)).ToList();
            return texts.Count == 0 ? null : string.Join("\n\n", texts);
        }
    }
}
