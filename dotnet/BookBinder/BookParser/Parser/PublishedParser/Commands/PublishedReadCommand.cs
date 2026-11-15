using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Windows.Input;

using WriterWorker.Models;
using WriterWorker.Parser.PublishedParser.Contents;

namespace WriterWorker.Parser.PublishedParser.Commands
{
    /// <summary>
    /// Reads every published book below a published root and exposes one
    /// <see cref="PublishedListEntry"/> per version folder, so the list page binds the same model
    /// the book pages and the PDF export use.
    /// The command parameter is the folder to read; executing it without a parameter re-reads
    /// the folder used last.
    /// </summary>
    public sealed class PublishedReadCommand : ICommand, INotifyPropertyChanged
    {
        private string? _rootFolder;
        private string _status = "No published folder loaded.";
        private string? _error;
        private PublishedListEntry? _selectedEdition;

        /// <summary>Editions found by the last read, newest book first.</summary>
        public ObservableCollection<PublishedListEntry> Editions { get; } = [];

        /// <summary>Folder that was actually read (the resolved published root).</summary>
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

        /// <summary>Reason the folder or a version could not be read.</summary>
        public string? Error
        {
            get => _error;
            private set => Set(ref _error, value);
        }

        public PublishedListEntry? SelectedEdition
        {
            get => _selectedEdition;
            set => Set(ref _selectedEdition, value);
        }

        public int EditionCount => Editions.Count;

        public int BookCount => Editions.Select(edition => edition.BookName).Distinct().Count();

        public bool HasEditions => Editions.Count > 0;

        /// <summary>Raised after every read, whether or not editions were found.</summary>
        public event EventHandler? EditionsLoaded;

        public bool CanExecute(object? parameter) => true;

        public void Execute(object? parameter) => Read(parameter as string ?? _rootFolder);

        public void Reload() => Read(_rootFolder);

        public void Read(string? folder)
        {
            Error = null;

            string? root;
            try
            {
                root = PublishedLibrary.ResolveRoot(folder);
                if (root is null && string.IsNullOrWhiteSpace(folder))
                {
                    root = PublishedLibrary.FindDefaultRoot();
                }
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                root = null;
                Error = exception.Message;
            }

            RootFolder = root;
            Editions.Clear();

            if (root is null)
            {
                Status = string.IsNullOrWhiteSpace(folder)
                    ? "Select the published folder that holds the editions."
                    : $"Folder not found: {folder}";
                SelectedEdition = null;
                Complete();
                return;
            }

            try
            {
                foreach (var entry in PublishedLibrary.Scan(root))
                {
                    var latest = entry.Latest;
                    foreach (var version in entry.Versions)
                    {
                        Editions.Add(new PublishedListEntry
                        {
                            FolderPath = version.FolderPath,
                            BookName = entry.FolderName,
                            Title = entry.Title,
                            VersionText = version.DisplayName,
                            PublishedAt = version.PublishedAt,
                            ChapterCount = version.ChapterCount,
                            IsLatest = ReferenceEquals(version, latest),
                            Error = entry.Error,
                            Source = BookSource.Published,
                        });
                    }
                }

                Status = Editions.Count == 0
                    ? $"No published editions found in {root}"
                    : $"{BookCount} book(s), {Editions.Count} edition(s) in {root}";
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                Error = exception.Message;
                Status = $"Could not read {root}";
            }

            SelectedEdition = Editions.FirstOrDefault();
            Complete();
        }

        private void Complete()
        {
            OnPropertyChanged(nameof(EditionCount));
            OnPropertyChanged(nameof(BookCount));
            OnPropertyChanged(nameof(HasEditions));
            EditionsLoaded?.Invoke(this, EventArgs.Empty);
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
