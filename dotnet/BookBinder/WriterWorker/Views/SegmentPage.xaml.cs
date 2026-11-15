using System;
using System.Linq;
using System.Text;
using System.Windows.Controls;
using WriterWorker.Models;
using WriterWorker.Themes;

namespace WriterWorker.Views
{
    /// <summary>
    /// Shows every available text of one segment (final, writer, editor, translator and each
    /// saved version) in tabs. The texts come from the parsed <see cref="Segment"/>.
    /// </summary>
    public partial class SegmentPage : UserControl, IBookPage
    {
        public SegmentPage()
        {
            InitializeComponent();
            BookTheme.Ensure(this);
        }

        public SegmentPage(Segment segment, string? chapterTitle = null)
            : this()
            => Load(segment, chapterTitle);

        public Segment? Segment { get; private set; }

        public string HeaderTitle { get; private set; } = string.Empty;

        string IBookPage.Title => HeaderTitle;

        /// <summary>Kind of page, shown in the header badge.</summary>
        public string WindowTitle => "Segment";

        public string CreatedBy { get; private set; } = BookMeta.Unknown;

        public string CreatedOn { get; private set; } = BookMeta.Unknown;

        public string HeaderSubtitle { get; private set; } = string.Empty;

        public string HeaderStats { get; private set; } = string.Empty;

        public string StatusText { get; private set; } = string.Empty;

        public string Directory { get; private set; } = string.Empty;

        private void Load(Segment segment, string? chapterTitle)
        {
            Segment = segment;

            HeaderTitle = FirstNonEmpty(segment.Title, DescriptiveName(segment), $"Segment {segment.Index}");
            HeaderSubtitle = JoinParts(chapterTitle, $"Segment {segment.Index}", segment.Name, segment.State);
            HeaderStats = JoinParts(
                $"{segment.WordCount:N0} words",
                segment.WordTarget > 0 ? $"target {segment.WordTarget:N0}" : null,
                $"text: {segment.TextSource ?? "none"}");
            StatusText = segment.TextSource is null or "none"
                ? "No text has been written for this segment yet."
                : $"{CountTabs(segment)} text variant(s) available.";
            Directory = segment.FolderPath ?? string.Empty;
            CreatedBy = BookMeta.Text(segment.CreatedBy);
            CreatedOn = BookMeta.Date(segment.CreatedOn, segment.FolderPath);

            AddTab("Final", segment.Body, "No text yet.");
            AddDistinctTab("Latest", segment.LatestText, segment.Body);
            AddDistinctTab("Writer", segment.WriterText, segment.Body);
            AddDistinctTab("Editor", segment.EditorText, segment.Body);
            AddDistinctTab("Translator", segment.TranslatedText, segment.Body);

            foreach (var version in segment.EditorVersions)
            {
                AddTab($"Editor v{version.Version}", version.Text, "Empty snapshot.");
            }

            foreach (var version in segment.Versions)
            {
                AddTab($"v{version.Version}", version.Text, "Empty snapshot.");
            }

            if (segment.FurtherReferences.Count > 0)
            {
                AddTab("References", FormatReferences(segment), "No references.");
            }

            DataContext = null;
            DataContext = this;
        }

        private void AddDistinctTab(string header, string? text, string? current)
        {
            if (string.IsNullOrWhiteSpace(text) || string.Equals(text, current, StringComparison.Ordinal))
            {
                return;
            }

            AddTab(header, text, string.Empty);
        }

        private void AddTab(string header, string? text, string placeholder)
            => TextTabs.Items.Add(TextTab.Create(this, header, text, placeholder));

        private static int CountTabs(Segment segment)
            => (string.IsNullOrWhiteSpace(segment.Body) ? 0 : 1)
               + new[] { segment.LatestText, segment.WriterText, segment.EditorText, segment.TranslatedText }
                   .Count(text => !string.IsNullOrWhiteSpace(text))
               + segment.EditorVersions.Count
               + segment.Versions.Count;

        private static string FormatReferences(Segment segment)
        {
            var builder = new StringBuilder();
            foreach (var reference in segment.FurtherReferences)
            {
                builder.Append(reference.Number).Append(". ").AppendLine(reference.Text);
                if (!string.IsNullOrWhiteSpace(reference.WebLink))
                {
                    builder.Append("    ").AppendLine(reference.WebLink);
                }

                builder.AppendLine();
            }

            return builder.ToString().TrimEnd();
        }

        private static string? DescriptiveName(Segment segment)
            => string.Equals(segment.Name, segment.Index.ToString(), StringComparison.Ordinal)
                ? null
                : segment.Name;

        private static string FirstNonEmpty(params string?[] values)
            => values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? string.Empty;

        private static string JoinParts(params string?[] parts)
            => string.Join("  ·  ", parts.Where(part => !string.IsNullOrWhiteSpace(part)));
    }
}
