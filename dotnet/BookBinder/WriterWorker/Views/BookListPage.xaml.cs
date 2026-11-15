using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

using Microsoft.Win32;

using WriterWorker.Controller;
using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Commands;
using WriterWorker.Parser.PublishedParser.Commands;
using WriterWorker.Themes;

namespace WriterWorker.Views
{
    /// <summary>
    /// Lists the books of a pipeline root (defaults to the pipeline folder of the current
    /// workspace) and opens the selected book in a <see cref="BookPage"/> tab, and lists the
    /// published editions of a published root and opens them in a <see cref="BookViewPage"/> tab.
    /// </summary>
    public partial class BookListPage : UserControl, INotifyPropertyChanged, IBookPage
    {
        private readonly IBookPageHost? _host;
        private readonly BookReadCommand _reader = new();
        private readonly PublishedReadCommand _publishedReader = new();
        private string _rootFolderText = string.Empty;
        private string _publishedRootFolderText = string.Empty;

        public BookListPage()
            : this(null, null)
        {
        }

        /// <param name="rootFolder">
        /// Folder of the main window. A book folder, a workspaces folder or a pipeline folder are
        /// all accepted; when null the pipeline folder is located automatically.
        /// </param>
        /// <param name="host">Host that shows the book pages as tabs.</param>
        public BookListPage(string? rootFolder, IBookPageHost? host)
        {
            InitializeComponent();
            BookTheme.Ensure(this);
            _host = host;
            DataContext = this;

            _reader.BooksLoaded += (_, _) => UpdateTitle();
            _publishedReader.EditionsLoaded += (_, _) => UpdateTitle();

            // The commands resolve the roots themselves (a selected book, a workspaces folder, a
            // pipeline/published folder, or the folder located automatically), so the page only
            // shows the folder that was actually read.
            _reader.Read(rootFolder);
            RootFolderText = _reader.RootFolder ?? rootFolder ?? string.Empty;

            _publishedReader.Read(null);
            PublishedRootFolderText = _publishedReader.RootFolder ?? string.Empty;
        }

        /// <summary>Reads the book plans of the pipeline root; the pipeline grid binds to it.</summary>
        public object Reader => _reader;

        /// <summary>Reads the editions of the published root; the published grid binds to it.</summary>
        public object PublishedReader => _publishedReader;

        public string TabTitle
        {
            get
            {
                var pipeline = _reader.BookCount;
                var published = _publishedReader.EditionCount;

                return (pipeline, published) switch
                {
                    (0, 0) => "Books",
                    (0, _) => $"Books ({published} published)",
                    (_, 0) => $"Books ({pipeline})",
                    _ => $"Books ({pipeline} + {published} published)",
                };
            }
        }

        string IBookPage.Title => TabTitle;

        public string HeaderTitle => TabTitle;

        /// <summary>Kind of page, shown in the header badge.</summary>
        public string WindowTitle => "Book List";

        /// <summary>The list itself is created by the current user when they open it.</summary>
        public string CreatedBy => BookMeta.CurrentUser;

        public string CreatedOn => BookMeta.FolderCreatedOn(RootFolderText);

        public string RootFolderText
        {
            get => _rootFolderText;
            set
            {
                if (string.Equals(_rootFolderText, value, StringComparison.Ordinal))
                {
                    return;
                }

                _rootFolderText = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(CreatedOn));
            }
        }

        /// <summary>Folder the published editions are read from.</summary>
        public string PublishedRootFolderText
        {
            get => _publishedRootFolderText;
            set
            {
                if (string.Equals(_publishedRootFolderText, value, StringComparison.Ordinal))
                {
                    return;
                }

                _publishedRootFolderText = value;
                OnPropertyChanged();
            }
        }

        public event PropertyChangedEventHandler? PropertyChanged;

        private void UpdateTitle()
        {
            OnPropertyChanged(nameof(HeaderTitle));
            OnPropertyChanged(nameof(CreatedOn));
            _host?.UpdatePageTitle(this, TabTitle);
        }

        private void Browse_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFolderDialog
            {
                Title = "Select the pipeline folder",
                Multiselect = false,
                InitialDirectory = _reader.RootFolder ?? RootFolderText,
            };

            if (dialog.ShowDialog(Window.GetWindow(this)) != true)
            {
                return;
            }

            RootFolderText = dialog.FolderName;
            _reader.Read(RootFolderText);
        }

        private void Refresh_Click(object sender, RoutedEventArgs e) => _reader.Read(RootFolderText);

        private void Open_Click(object sender, RoutedEventArgs e) => OpenSelectedBook();

        private void RootBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key != Key.Enter)
            {
                return;
            }

            _reader.Read(RootFolderText);
            e.Handled = true;
        }

        private void BooksGrid_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            if (e.ChangedButton == MouseButton.Left)
            {
                OpenSelectedBook();
            }
        }

        private void OpenSelectedBook()
        {
            if (BooksGrid.SelectedItem is not BookListEntry book)
            {
                return;
            }

            _host?.ShowPage(new BookPageRequest
            {
                Title = book.DisplayName,
                Glyph = BookGlyphs.Book,
                Key = $"book:{book.FolderPath}",
                Content = new BookPage(book.FolderPath, _host),
            });
        }

        private void PublishedBrowse_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFolderDialog
            {
                Title = "Select the published folder",
                Multiselect = false,
                InitialDirectory = _publishedReader.RootFolder ?? PublishedRootFolderText,
            };

            if (dialog.ShowDialog(Window.GetWindow(this)) != true)
            {
                return;
            }

            PublishedRootFolderText = dialog.FolderName;
            _publishedReader.Read(PublishedRootFolderText);
        }

        private void PublishedRefresh_Click(object sender, RoutedEventArgs e)
            => _publishedReader.Read(PublishedRootFolderText);

        private void PublishedOpen_Click(object sender, RoutedEventArgs e) => OpenSelectedEdition();

        private void PublishedRootBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key != Key.Enter)
            {
                return;
            }

            _publishedReader.Read(PublishedRootFolderText);
            e.Handled = true;
        }

        private void PublishedGrid_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            if (e.ChangedButton == MouseButton.Left)
            {
                OpenSelectedEdition();
            }
        }

        private void OpenSelectedEdition()
        {
            if (PublishedGrid.SelectedItem is not PublishedListEntry edition)
            {
                return;
            }

            Book book;
            try
            {
                book = BookParsers.Parse(edition.FolderPath);
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException
                or InvalidOperationException or System.Text.Json.JsonException)
            {
                MessageBox.Show(
                    Window.GetWindow(this),
                    $"Could not read the published edition:\n{edition.FolderPath}\n\n{exception.Message}",
                    "Open published edition",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
                return;
            }

            _host?.ShowPage(new BookPageRequest
            {
                Title = edition.DisplayName,
                Glyph = BookGlyphs.Book,
                Key = $"published:{edition.FolderPath}",
                Content = new BookViewPage(book, edition.FolderPath),
            });
        }

        private void OnPropertyChanged([CallerMemberName] string? name = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    }
}
