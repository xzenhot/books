using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Threading;
using Microsoft.Win32;
using WriterWorker.Configuration;
using WriterWorker.Ctl;
using WriterWorker.Controller;
using WriterWorker.Models;
using WriterWorker.Themes;

namespace WriterWorker.Views
{
    /// <summary>
    /// Shows the whole book assembled from the text of every segment in the folder picked by the
    /// content-source dropdown (latest, editor, translator or writer — see <see cref="ContentSource"/>),
    /// falling back to the chapter text when no segment has content. The page reads the workspace
    /// through <see cref="BookParsers"/> and then works only with <see cref="Book"/>, so the
    /// reader, the status bar and the PDF export all see the same model. The result is shown in an
    /// editable RichTextBox with a Word-style formatting toolbar, and can be exported to an
    /// <c>.rtf</c> or <c>.pdf</c> file.
    /// </summary>
    public partial class BookViewPage : UserControl, IBookPage, INotifyPropertyChanged
    {
        private const string BookSeparator = "═══════════════";
        private const string ChapterSeparator = "───────────────────";

        private readonly DispatcherTimer _statsTimer = new() { Interval = TimeSpan.FromMilliseconds(500) };

        private Func<Book>? _loadBook;
        private string _folderPath = string.Empty;
        private string _displayName = string.Empty;
        private Book? _book;
        private string _statusText = string.Empty;
        private string _editStatus = string.Empty;
        private bool _documentLoaded;
        private bool _edited;
        private bool _exporting;

        public BookViewPage()
        {
            InitializeComponent();
            ContentSourceBox.ItemsSource = ContentSource.Options;
            ContentSourceBox.SelectedItem = ContentSource.Selected;
            BookTheme.Ensure(this);
            _statsTimer.Tick += (_, _) =>
            {
                _statsTimer.Stop();
                UpdateEditStatus();
            };
        }

        public BookViewPage(string bookFolder)
            : this()
        {
            // A profile that travelled with the book - the copy inside a published edition, or one
            // shared with a printer - still names the folder the content is printed from.
            var folder = BookProfile.ContentFolderOf(bookFolder) ?? bookFolder;

            Load(
                () => BookParsers.Parse(folder),
                folder,
                Path.GetFileName(folder.TrimEnd(Path.DirectorySeparatorChar)));
        }

        /// <summary>
        /// Shows a book that was already parsed, for example a published edition read through
        /// <see cref="BookParsers"/>. The page works only with <see cref="Book"/>.
        /// </summary>
        public BookViewPage(Book book, string bookFolder)
            : this()
        {
            ArgumentNullException.ThrowIfNull(book);
            Load(
                () => book,
                bookFolder,
                book.Title ?? Path.GetFileName(bookFolder.TrimEnd(Path.DirectorySeparatorChar)));
        }

        public Book? Book => _book;

        /// <summary>The document shown in the reader, i.e. what the exporters write out.</summary>
        public FlowDocument Document => BookReader.Document;

        public string HeaderTitle { get; private set; } = string.Empty;

        string IBookPage.Title => HeaderTitle;

        /// <summary>Kind of page, shown in the header badge.</summary>
        public string WindowTitle => "Book";

        public string CreatedBy { get; private set; } = BookMeta.Unknown;

        public string CreatedOn { get; private set; } = BookMeta.Unknown;

        public string HeaderSubtitle { get; private set; } = string.Empty;

        public string HeaderStats { get; private set; } = string.Empty;

        public string StatusText
        {
            get => _statusText;
            private set
            {
                if (_statusText == value)
                {
                    return;
                }

                _statusText = value;
                OnPropertyChanged();
            }
        }

        /// <summary>Live word count of the edited document, shown in the middle of the status bar.</summary>
        public string EditStatus
        {
            get => _editStatus;
            private set
            {
                if (_editStatus == value)
                {
                    return;
                }

                _editStatus = value;
                OnPropertyChanged();
            }
        }

        public string FolderPath => _folderPath;

        public event PropertyChangedEventHandler? PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string? propertyName = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));

        /// <summary>The assembled book text: reviewed segments first, then the chapter text.</summary>
        public string AssembledText { get; private set; } = string.Empty;

        private void Load(Func<Book> loadBook, string bookFolder, string? displayName)
        {
            _loadBook = loadBook;
            _folderPath = bookFolder;
            _displayName = displayName ?? bookFolder;

            // Parsing stays with the loader; the page itself only sees the book model.
            _book = loadBook();

            var segmentTexts = _book.Chapters
                .SelectMany(chapter => chapter.Segments)
                .Select(segment => segment.Body)
                .Where(text => !string.IsNullOrWhiteSpace(text))
                .ToList();

            var useSegments = segmentTexts.Count > 0;
            AssembledText = useSegments
                ? AssembleFromSegments(_book)
                : AssembleFromChapters(_book);

            BookReader.Document = MarkdownFlow.Build(AssembledText);
            BookReader.Document.PageWidth = double.NaN;

            HeaderTitle = _book.Title ?? _displayName;
            HeaderSubtitle = JoinParts(_book.Name, _book.Language, _book.Form);
            HeaderStats = JoinParts(
                $"{_book.Chapters.Count} chapter(s)",
                $"{_book.WordCount:N0} words",
                useSegments
                    ? $"{segmentTexts.Count} segment(s) with text"
                    : $"{_book.CompletedChapterCount} completed chapter(s)");
            StatusText = useSegments
                ? $"Assembled from segment text: {segmentTexts.Count} segment(s) at the {_book.Stage} stage."
                : "No segment text found; showing the chapter text.";
            CreatedBy = BookMeta.Text(_book.Author);
            CreatedOn = BookMeta.Date(_book.CreatedOn, bookFolder);

            _documentLoaded = true;
            _edited = false;
            UpdateEditStatus();

            DataContext = null;
            DataContext = this;
        }

        private void ContentSourceBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ContentSourceBox.SelectedItem is not string source
                || string.Equals(source, ContentSource.Selected, StringComparison.Ordinal))
            {
                return;
            }

            if (_edited
                && MessageBox.Show(
                    Window.GetWindow(this),
                    "Loading the text from another content source discards your edits. Continue?",
                    "Content source",
                    MessageBoxButton.YesNo,
                    MessageBoxImage.Warning,
                    MessageBoxResult.No) != MessageBoxResult.Yes)
            {
                ContentSourceBox.SelectedItem = ContentSource.Selected;
                return;
            }

            ContentSource.Selected = source;

            if (_loadBook is not null)
            {
                Load(_loadBook, _folderPath, _displayName);
            }
        }

        private void BookReader_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (!_documentLoaded)
            {
                return;
            }

            _edited = true;
            _statsTimer.Stop();
            _statsTimer.Start();
        }

        private void UpdateEditStatus()
        {
            var words = CountWords(PdfExport.PlainText(BookReader.Document));
            EditStatus = _edited ? $"Edited · {words:N0} words" : $"{words:N0} words";
        }

        private static int CountWords(string text)
        {
            var count = 0;
            var inWord = false;

            foreach (var character in text)
            {
                if (char.IsWhiteSpace(character))
                {
                    inWord = false;
                }
                else if (!inWord)
                {
                    inWord = true;
                    count++;
                }
            }

            return count;
        }

        private static string AssembleFromSegments(Book book)
        {
            var builder = new StringBuilder();

            var title = book.Title;
            if (!string.IsNullOrWhiteSpace(title))
            {
                builder.AppendLine("# " + title);
                builder.AppendLine();
            }

            var emitted = false;
            foreach (var chapter in book.Chapters)
            {
                var segments = chapter.Segments
                    .Where(segment => !string.IsNullOrWhiteSpace(segment.Body))
                    .ToList();
                if (segments.Count == 0)
                {
                    continue;
                }

                if (emitted)
                {
                    builder.AppendLine();
                    builder.AppendLine(ChapterSeparator);
                }

                builder.AppendLine($"## Chapter {chapter.Index}: {FirstNonEmpty(chapter.Title, chapter.Name)}");
                builder.AppendLine();

                foreach (var segment in segments)
                {
                    if (segments.IndexOf(segment) > 0)
                    {
                        builder.AppendLine();
                        builder.AppendLine(BookSeparator);
                    }

                    builder.Append(segment.Body);
                    builder.AppendLine();
                }

                emitted = true;
            }

            return builder.ToString().TrimEnd();
        }

        private static string AssembleFromChapters(Book book)
        {
            var builder = new StringBuilder();

            var title = book.Title;
            if (!string.IsNullOrWhiteSpace(title))
            {
                builder.AppendLine("# " + title);
                builder.AppendLine();
            }

            foreach (var chapter in book.Chapters)
            {
                var text = chapter.Body;
                if (string.IsNullOrWhiteSpace(text))
                {
                    continue;
                }

                if (builder.Length > 0)
                {
                    builder.AppendLine();
                    builder.AppendLine(ChapterSeparator);
                }

                builder.AppendLine($"## Chapter {chapter.Index}: {FirstNonEmpty(chapter.Title, chapter.Name)}");
                builder.AppendLine();
                builder.Append(text);
                builder.AppendLine();
            }

            return builder.ToString().TrimEnd();
        }

        private static string FirstNonEmpty(params string?[] values)
            => values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? string.Empty;

        private static string JoinParts(params string?[] parts)
            => string.Join("  ·  ", parts.Where(part => !string.IsNullOrWhiteSpace(part)));

        private void Export_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new SaveFileDialog
            {
                Title = "Export assembled book",
                Filter = RtfExport.RtfFileFilter,
                DefaultExt = ".rtf",
                AddExtension = true,
                OverwritePrompt = true,
                FileName = Sanitize(HeaderTitle) + ".rtf",
            };

            if (dialog.ShowDialog(Window.GetWindow(this)) != true)
            {
                return;
            }

            try
            {
                RtfExport.Save(BookReader.Document, dialog.FileName);
                StatusText = $"Exported {dialog.FileName}";
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or ArgumentException
                or NotSupportedException)
            {
                StatusText = "Export failed";
                MessageBox.Show(
                    Window.GetWindow(this),
                    $"The book could not be exported.\n\n{exception.Message}",
                    "Export assembled book",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
        }

        private async void ExportPdf_Click(object sender, RoutedEventArgs e)
        {
            if (_exporting)
            {
                return;
            }

            var requested = PdfExportOptions.Current.Clone();
            requested.Title = HeaderTitle;
            requested.Author = CreatedBy == BookMeta.Unknown ? null : CreatedBy;

            if (!PdfPageSetupDialog.TryAsk(
                    Window.GetWindow(this),
                    requested,
                    out var options,
                    bookFolder: FolderPath))
            {
                return;
            }

            var dialog = new SaveFileDialog
            {
                Title = "Export assembled book to PDF",
                Filter = PdfExport.PdfFileFilter,
                DefaultExt = ".pdf",
                AddExtension = true,
                OverwritePrompt = true,
                FileName = Sanitize(HeaderTitle) + ".pdf",
            };

            if (dialog.ShowDialog(Window.GetWindow(this)) != true)
            {
                return;
            }

            var path = dialog.FileName;

            // An edited reader holds text the segments do not have, so it is exported as it is.
            var fromSegments = options.Layout == PdfLayout.ChapterPages && _book is not null && !_edited;

            _exporting = true;
            ShowProgress($"Generating {Path.GetFileName(path)}...");
            StatusText = $"Generating {Path.GetFileName(path)}...";
            Mouse.OverrideCursor = Cursors.Wait;

            try
            {
                if (fromSegments)
                {
                    // The segment text is plain data, so the layout and rendering run off this thread.
                    var book = _book!;
                    var settings = options.Clone();
                    await Task.Run(() => PdfExport.Save(book, path, settings));
                }
                else
                {
                    // The reader's FlowDocument belongs to this thread, so it is rendered here.
                    // Yielding lets the progress bar paint before the rendering starts.
                    await Dispatcher.Yield(DispatcherPriority.Render);
                    PdfExport.Save(BookReader.Document, path, options);
                }

                StatusText = $"Exported {path}";
                MessageBox.Show(
                    Window.GetWindow(this),
                    $"The PDF was generated.\n\n{path}",
                    "Export assembled book to PDF",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            }
            catch (Exception exception) when (exception is IOException
                or UnauthorizedAccessException
                or ArgumentException
                or NotSupportedException
                or InvalidOperationException)
            {
                StatusText = "PDF export failed";
                MessageBox.Show(
                    Window.GetWindow(this),
                    $"The book could not be exported to PDF.\n\n{exception.Message}",
                    "Export assembled book to PDF",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                Mouse.OverrideCursor = null;
                HideProgress();
                _exporting = false;
            }
        }

        /// <summary>
        /// Shows the progress strip under the status bar. A null <paramref name="fraction"/> runs the
        /// bar without a value; <see cref="HideProgress"/> removes the strip again.
        /// </summary>
        internal void ShowProgress(string? message, double? fraction = null)
        {
            ProgressText.Text = message ?? string.Empty;
            ExportProgressBar.IsIndeterminate = fraction is null;
            ExportProgressBar.Value = fraction is null ? 0 : Math.Clamp(fraction.Value, 0, 1) * 100;
            ProgressHost.Visibility = Visibility.Visible;
        }

        /// <summary>Hides the progress strip and clears its message.</summary>
        internal void HideProgress()
        {
            ProgressHost.Visibility = Visibility.Collapsed;
            ProgressText.Text = string.Empty;
            ExportProgressBar.IsIndeterminate = true;
            ExportProgressBar.Value = 0;
        }

        private static string Sanitize(string name)
        {
            var value = string.IsNullOrWhiteSpace(name) ? "Book" : name.Trim();
            foreach (var invalid in Path.GetInvalidFileNameChars())
            {
                value = value.Replace(invalid, '_');
            }

            return value;
        }
    }
}
