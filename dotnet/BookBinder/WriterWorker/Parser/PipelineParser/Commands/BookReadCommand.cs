using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Windows.Input;

using WriterWorker.Models;
using WriterWorker.Parser.PipelineParser.Contents;

namespace WriterWorker.Parser.PipelineParser.Commands
{
    /// <summary>
    /// Reads the plan (<c>book.json</c> → <see cref="BookModel"/>) of every book folder below a
    /// pipeline root and exposes them as <see cref="BookListEntry"/> rows, so the list page binds
    /// the same model the book pages and the PDF export use.
    /// The command parameter is the folder to read; executing it without a parameter re-reads
    /// the folder used last.
    /// </summary>
    internal sealed class BookReadCommand : ICommand, INotifyPropertyChanged
    {
        private string? _rootFolder;
        private string _status = "No pipeline folder loaded.";
        private string? _error;
        private BookListEntry? _selectedBook;

        /// <summary>Books found by the last read, in folder order.</summary>
        public ObservableCollection<BookListEntry> Books { get; } = [];

        /// <summary>Folder that was actually read (the resolved pipeline root).</summary>
        public string? RootFolder
        {
            get => _rootFolder;
            private set => Set(ref _rootFolder, value);
        }

        public string Status
        {
            get => _status;
            private set => Set(ref _status, value);
        }

        /// <summary>Reason the folder or a plan could not be read.</summary>
        public string? Error
        {
            get => _error;
            private set => Set(ref _error, value);
        }

        public BookListEntry? SelectedBook
        {
            get => _selectedBook;
            set => Set(ref _selectedBook, value);
        }

        public int BookCount => Books.Count;

        public bool HasBooks => Books.Count > 0;

        /// <summary>Raised after every read, whether or not books were found.</summary>
        public event EventHandler? BooksLoaded;

        public bool CanExecute(object? parameter) => true;

        public void Execute(object? parameter) => Read(parameter as string ?? _rootFolder);

        public void Reload() => Read(_rootFolder);

        public void Read(string? folder)
        {
            Error = null;

            string? root;
            try
            {
                root = BookLibrary.ResolveRoot(folder);
                if (root is null && string.IsNullOrWhiteSpace(folder))
                {
                    root = BookLibrary.FindDefaultRoot();
                }
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                root = null;
                Error = exception.Message;
            }

            RootFolder = root;
            Books.Clear();

            if (root is null)
            {
                Status = string.IsNullOrWhiteSpace(folder)
                    ? "Select the pipeline folder that holds the books."
                    : $"Folder not found: {folder}";
                SelectedBook = null;
                Complete();
                return;
            }

            try
            {
                foreach (var book in BookLibrary.Scan(root))
                {
                    Books.Add(ToEntry(book));
                }

                Status = Books.Count == 0
                    ? $"No books found in {root}"
                    : $"{Books.Count} book(s) in {root}";
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                Error = exception.Message;
                Status = $"Could not read {root}";
            }

            SelectedBook = Books.FirstOrDefault();
            Complete();
        }

        private static BookListEntry ToEntry(BookEntry entry) => new()
        {
            FolderPath = entry.FolderPath,
            FolderName = entry.FolderName,
            DisplayName = entry.DisplayName,
            Title = entry.Plan?.BookLongTitle ?? entry.Plan?.BookName,
            Language = entry.Language,
            Form = entry.Form,
            Gist = entry.Gist,
            ChapterCount = entry.ChapterCount,
            SegmentCount = entry.SegmentCount,
            PlanState = entry.PlanState,
            Error = entry.Error,
            Source = BookSource.Pipeline,
        };

        private void Complete()
        {
            OnPropertyChanged(nameof(BookCount));
            OnPropertyChanged(nameof(HasBooks));
            BooksLoaded?.Invoke(this, EventArgs.Empty);
        }

        public event EventHandler? CanExecuteChanged
        {
            add => CommandManager.RequerySuggested += value;
            remove => CommandManager.RequerySuggested -= value;
        }

        public event PropertyChangedEventHandler? PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string? name = null)
            => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));

        private void Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
        {
            if (EqualityComparer<T>.Default.Equals(field, value))
            {
                return;
            }

            field = value;
            OnPropertyChanged(name);
        }
    }
}
