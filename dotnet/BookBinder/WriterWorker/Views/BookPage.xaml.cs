using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using WriterWorker.Controller;
using WriterWorker.Models;
using WriterWorker.Themes;

namespace WriterWorker.Views
{
    /// <summary>
    /// Shows the chapters of one book. The book is read through <see cref="BookParsers"/>, so the
    /// page only ever works with <see cref="Book"/>; double-clicking a chapter opens the
    /// <see cref="ChapterPage"/> tab.
    /// </summary>
    public partial class BookPage : UserControl, IBookPage
    {
        private readonly IBookPageHost? _host;
        private string _folderPath = string.Empty;
        private string _displayName = string.Empty;

        public BookPage()
        {
            InitializeComponent();
            BookTheme.Ensure(this);
        }

        public BookPage(string bookFolder, IBookPageHost? host = null)
            : this()
        {
            _host = host;
            Load(bookFolder);
        }

        public Book? Book { get; private set; }

        public IReadOnlyList<string> DocumentNames { get; private set; } = [];

        public string HeaderTitle { get; private set; } = string.Empty;

        string IBookPage.Title => HeaderTitle;

        /// <summary>Kind of page, shown in the header badge.</summary>
        public string WindowTitle => "Book";

        public string CreatedBy { get; private set; } = BookMeta.Unknown;

        public string CreatedOn { get; private set; } = BookMeta.Unknown;

        public string HeaderSubtitle { get; private set; } = string.Empty;

        public string HeaderStats { get; private set; } = string.Empty;

        public string StatusText { get; private set; } = string.Empty;

        public string FolderPath => _folderPath;

        private void Load(string bookFolder)
        {
            _folderPath = bookFolder;
            _displayName = FolderName(bookFolder);

            Mouse.OverrideCursor = Cursors.Wait;
            try
            {
                Book = BookParsers.Parse(bookFolder);
                DocumentNames = Book.Documents.Keys
                    .OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
                    .ToList();
                StatusText = $"{Book.ChapterCount} chapter(s) · {Book.CompletedChapterCount} completed · double-click a chapter to open it.";
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or InvalidDataException
                or InvalidOperationException
                or NotSupportedException
                or ArgumentException
                or JsonException)
            {
                Book = null;
                DocumentNames = [];
                StatusText = exception.Message;
            }
            finally
            {
                Mouse.OverrideCursor = null;
            }

            HeaderTitle = Book?.Title ?? _displayName;
            HeaderSubtitle = JoinParts(Book?.Name, Book?.Language, Book?.Form);
            HeaderStats = Book is null
                ? Book?.Gist ?? string.Empty
                : $"{Book.WordCount:N0} words · {Book.ChapterCount} chapter(s) · {Book.SegmentCount:N0} segment(s)";
            CreatedBy = BookMeta.Text(Book?.Author);
            CreatedOn = BookMeta.Date(Book?.CreatedOn, bookFolder);

            // Plain properties: reset the data context so every binding re-reads them.
            DataContext = null;
            DataContext = this;

            if (DocumentNames.Count > 0)
            {
                DocumentsList.SelectedIndex = 0;
            }

            _host?.UpdatePageTitle(this, HeaderTitle);
        }

        private static string FolderName(string folder)
        {
            var trimmed = folder.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            var name = Path.GetFileName(trimmed);
            return string.IsNullOrEmpty(name) ? folder : name;
        }

        private static string JoinParts(params string?[] parts)
            => string.Join("  ·  ", parts.Where(part => !string.IsNullOrWhiteSpace(part)));

        private void Refresh_Click(object sender, RoutedEventArgs e)
        {
            if (_folderPath.Length > 0)
            {
                Load(_folderPath);
            }
        }

        private void BookPage_Click(object sender, RoutedEventArgs e)
        {
            if (_folderPath.Length == 0)
            {
                return;
            }

            _host?.ShowPage(new BookPageRequest
            {
                Title = FirstNonEmpty(HeaderTitle, _displayName),
                Glyph = BookGlyphs.Book,
                Key = $"bookview:{FolderPath}",
                Content = new BookViewPage(FolderPath),
            });
        }

        private void ChaptersGrid_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            if (e.ChangedButton != MouseButton.Left || ChaptersGrid.SelectedItem is not Chapter chapter)
            {
                return;
            }

            _host?.ShowPage(new BookPageRequest
            {
                Title = FirstNonEmpty(chapter.Title, chapter.Name, $"Chapter {chapter.Index}"),
                Glyph = BookGlyphs.Chapter,
                Key = chapter.FolderPath is { Length: > 0 } directory
                    ? $"chapter:{directory}"
                    : $"chapter:{FolderPath}|{chapter.Index}",
                Content = new ChapterPage(chapter, HeaderTitle, _host),
            });
        }

        private static string FirstNonEmpty(params string?[] values)
            => values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? string.Empty;

        private void DocumentsList_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            DocumentText.Text = DocumentsList.SelectedItem is string name
                && Book is not null
                && Book.Documents.TryGetValue(name, out var text)
                    ? text
                    : string.Empty;
        }
    }
}
