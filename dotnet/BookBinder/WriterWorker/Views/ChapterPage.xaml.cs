using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using WriterWorker.Models;
using WriterWorker.Themes;

namespace WriterWorker.Views
{
    /// <summary>
    /// Shows the segments of one chapter and the assembled chapter text; double-clicking a
    /// segment opens the <see cref="SegmentPage"/> tab. The page is filled from
    /// <see cref="Chapter"/>, which the parser produced.
    /// </summary>
    public partial class ChapterPage : UserControl, IBookPage
    {
        private readonly IBookPageHost? _host;

        public ChapterPage()
        {
            InitializeComponent();
            BookTheme.Ensure(this);
        }

        public ChapterPage(Chapter chapter, string? bookTitle = null, IBookPageHost? host = null)
            : this()
        {
            _host = host;
            Load(chapter, bookTitle);
        }

        public Chapter? Chapter { get; private set; }

        public string HeaderTitle { get; private set; } = string.Empty;

        string IBookPage.Title => HeaderTitle;

        /// <summary>Kind of page, shown in the header badge.</summary>
        public string WindowTitle => "Chapter";

        public string CreatedBy { get; private set; } = BookMeta.Unknown;

        public string CreatedOn { get; private set; } = BookMeta.Unknown;

        public string HeaderSubtitle { get; private set; } = string.Empty;

        public string HeaderStats { get; private set; } = string.Empty;

        public string StatusText { get; private set; } = string.Empty;

        public string Directory { get; private set; } = string.Empty;

        private void Load(Chapter chapter, string? bookTitle)
        {
            Chapter = chapter;
            ChapterTextBox.Text = chapter.Body ?? string.Empty;

            HeaderTitle = FirstNonEmpty(chapter.Title, chapter.Name, $"Chapter {chapter.Index}");
            HeaderSubtitle = JoinParts(
                bookTitle,
                $"Chapter {chapter.Index}",
                chapter.Name,
                chapter.State,
                chapter.Status);
            HeaderStats = JoinParts(
                $"{chapter.Segments.Count} segment(s)",
                $"{chapter.WordCount:N0} words",
                chapter.WordTarget > 0 ? $"target {chapter.WordTarget:N0}" : null,
                chapter.CompletedDate is null ? null : $"completed {chapter.CompletedDate}");
            StatusText = chapter.Segments.Count == 0
                ? "This chapter has no segments."
                : "Double-click a segment to read its text.";
            Directory = chapter.FolderPath ?? string.Empty;
            CreatedBy = BookMeta.Text(chapter.CreatedBy);
            CreatedOn = BookMeta.Date(chapter.CreatedOn, chapter.FolderPath);

            AddTextTab("Context", chapter.Context);
            AddTextTab("Draft", chapter.Draft);

            DataContext = null;
            DataContext = this;

            _host?.UpdatePageTitle(this, HeaderTitle);
        }

        private void AddTextTab(string header, string? text)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return;
            }

            ChapterTabs.Items.Add(TextTab.Create(this, header, text));
        }

        private static string FirstNonEmpty(params string?[] values)
            => values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? string.Empty;

        private static string JoinParts(params string?[] parts)
            => string.Join("  ·  ", parts.Where(part => !string.IsNullOrWhiteSpace(part)));

        private void SegmentsGrid_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            if (e.ChangedButton != MouseButton.Left || SegmentsGrid.SelectedItem is not Segment segment)
            {
                return;
            }

            _host?.ShowPage(new BookPageRequest
            {
                Title = FirstNonEmpty(segment.Title, segment.Name, $"Segment {segment.Index}"),
                Glyph = BookGlyphs.Segment,
                Key = segment.FolderPath is { Length: > 0 } directory
                    ? $"segment:{directory}"
                    : $"segment:{Directory}|{segment.Index}",
                Content = new SegmentPage(segment, HeaderTitle),
            });
        }
    }
}
