using System;
using System.Collections.Generic;
using System.Linq;

using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Models;

namespace WriterWorker.Parser.PipelineParser.Contents
{
    /// <summary>
    /// One segment folder (<c>chapters/{n}/segments/{i}</c>) with every text variant found in it.
    /// </summary>
    public sealed class SegmentContent
    {
        public int Index { get; set; }

        public string Name { get; set; } = string.Empty;

        public string? Title { get; set; }

        public string? Summary { get; set; }

        /// <summary>Pipeline state from segment.json (enriched, written, edited, ...).</summary>
        public string? State { get; set; }

        public int WordTarget { get; set; }

        public int WordCount { get; set; }

        /// <summary>Author inherited from the book plan.</summary>
        public string? CreatedBy { get; set; }

        /// <summary>Segment folder creation time, or the parent chapter completion date.</summary>
        public string? CreatedOn { get; set; }

        /// <summary>Newest pipeline output: <c>segments/{i}/latest/segment.md</c>.</summary>
        public string? LatestText { get; set; }

        /// <summary>Flat layout used by older workspaces: <c>segments/{i}/segment.md</c>.</summary>
        public string? SegmentText { get; set; }

        /// <summary>Writer output: <c>segments/{i}/writer/segment.md</c>.</summary>
        public string? WriterText { get; set; }

        /// <summary>Editor output: <c>segments/{i}/editor/segment.md</c>.</summary>
        public string? EditorText { get; set; }

        /// <summary>Translator output: <c>segments/{i}/translator/segment.md</c>.</summary>
        public string? TranslatedText { get; set; }

        /// <summary>Editor snapshots from <c>segments/{i}/editor/version</c>.</summary>
        public List<SegmentVersion> EditorVersions { get; } = new List<SegmentVersion>();

        /// <summary>Snapshots from <c>segments/{i}/version</c>.</summary>
        public List<SegmentVersion> Versions { get; } = new List<SegmentVersion>();

        public List<FurtherReferenceModel> FurtherReferences { get; } = new List<FurtherReferenceModel>();

        public string? Directory { get; set; }

        /// <summary>
        /// Texts in the order the workspace folders are produced: <c>latest</c>, <c>editor</c>,
        /// the flat <c>segment.md</c>, <c>writer</c>, <c>translator</c>, then saved snapshots.
        /// </summary>
        private IEnumerable<(string Source, string? Text)> TextCandidates()
        {
            yield return ("latest", LatestText);
            yield return ("editor", EditorText);
            yield return ("segment", SegmentText);
            yield return ("writer", WriterText);
            yield return ("translator", TranslatedText);
            yield return ("editor version", EditorVersions.LastOrDefault()?.Text);
            yield return ("version", Versions.LastOrDefault()?.Text);
        }

        /// <summary>Best available text, newest pipeline folder first.</summary>
        public string? Text =>
            TextCandidates().Select(candidate => candidate.Text)
                .FirstOrDefault(text => !string.IsNullOrWhiteSpace(text));

        /// <summary>Text of the folder picked in the content-source dropdown.</summary>
        private string? PreferredText => ContentSource.Selected switch
        {
            ContentSource.Editor => EditorText,
            ContentSource.Translated => TranslatedText,
            ContentSource.Writer => WriterText,
            _ => LatestText,
        };

        /// <summary>
        /// Text the book design page renders: the selected content source first, then the default
        /// <c>latest</c> → <c>editor</c> → <c>writer</c> chain when that folder has no text.
        /// </summary>
        public string? DisplayText => FirstNonEmpty(PreferredText, LatestText, EditorText, WriterText);

        /// <summary>
        /// Folder that supplied <see cref="DisplayText"/>: latest, editor, translator, writer or none.
        /// </summary>
        public string DisplayTextSource =>
            !string.IsNullOrWhiteSpace(PreferredText) ? ContentSource.FolderName(ContentSource.Selected)
            : !string.IsNullOrWhiteSpace(LatestText) ? "latest"
            : !string.IsNullOrWhiteSpace(EditorText) ? "editor"
            : !string.IsNullOrWhiteSpace(WriterText) ? "writer"
            : "none";

        /// <summary>Which folder produced <see cref="Text"/>, for display in the segment grids.</summary>
        public string TextSource =>
            TextCandidates()
                .FirstOrDefault(candidate => !string.IsNullOrWhiteSpace(candidate.Text))
                .Source ?? "none";

        private static string? FirstNonEmpty(params string?[] values) =>
            values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value));
    }

    public sealed class SegmentVersion
    {
        public int Version { get; init; }

        public string? Path { get; init; }

        public string? Text { get; init; }
    }
}
