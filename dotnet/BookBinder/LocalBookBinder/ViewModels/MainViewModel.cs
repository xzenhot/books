using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;
using System.Text;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;
using LocalBookBinder.Infrastructure;
using LocalBookBinder.Models;
using Microsoft.Win32;

namespace LocalBookBinder.ViewModels;

public sealed class MainViewModel : INotifyPropertyChanged
{
    private const long MaxPreviewBytes = 2 * 1024 * 1024;

    private static readonly HashSet<string> TextExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".txt", ".md", ".cs", ".xaml", ".xml", ".json", ".yml", ".yaml", ".props", ".targets",
        ".csproj", ".sln", ".config", ".ps1", ".psm1", ".html", ".htm", ".css", ".js", ".ts",
        ".tsx", ".jsx", ".csv", ".log", ".gitignore", ".editorconfig", ".sh", ".bat", ".cmd",
        ".sql", ".resx", ".manifest", ".ini", ".toml"
    };

    private DocumentTab? _selectedDocument;
    private bool _isSideBarVisible = true;
    private double _sideBarWidth = 260;
    private string _statusMessage = "Ready";
    private string? _folderPath;
    private string _activeActivity = "Explorer";
    private FileSystemWatcher? _watcher;
    private DispatcherTimer? _refreshTimer;

    public MainViewModel()
    {
        OpenFolderCommand = new RelayCommand(OpenFolder);
        OpenFileCommand = new RelayCommand(OpenFile);
        CloseDocumentCommand = new RelayCommand(parameter => CloseDocument(parameter as DocumentTab));
        CloseAllDocumentsCommand = new RelayCommand(CloseAllDocuments, () => Documents.Count > 0);
        ToggleSideBarCommand = new RelayCommand(() => IsSideBarVisible = !IsSideBarVisible);
        ShowExplorerCommand = new RelayCommand(ShowExplorer);
        RefreshCommand = new RelayCommand(RefreshExplorer);
        OpenSettingsCommand = new RelayCommand(OpenSettings);
        ExitCommand = new RelayCommand(() => Application.Current.Shutdown());
        AboutCommand = new RelayCommand(ShowAbout);
        BookListCommand = new RelayCommand(ShowBookList);
    }

    public SettingsViewModel Settings { get; } = new();

    public ObservableCollection<ThemeOption> Themes => Settings.ThemeOptions;

    public ObservableCollection<ExplorerNode> Roots { get; } = new();

    public ObservableCollection<DocumentTab> Documents { get; } = new();

    public ICommand OpenFolderCommand { get; }
    public ICommand OpenFileCommand { get; }
    public ICommand CloseDocumentCommand { get; }
    public ICommand CloseAllDocumentsCommand { get; }
    public ICommand ToggleSideBarCommand { get; }
    public ICommand ShowExplorerCommand { get; }
    public ICommand RefreshCommand { get; }
    public ICommand OpenSettingsCommand { get; }
    public ICommand ExitCommand { get; }
    public ICommand AboutCommand { get; }
    public ICommand BookListCommand { get; }

    public DocumentTab? SelectedDocument
    {
        get => _selectedDocument;
        set
        {
            if (ReferenceEquals(_selectedDocument, value)) return;
            _selectedDocument = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(SelectedPath));
            OnPropertyChanged(nameof(SelectedLanguage));
            OnPropertyChanged(nameof(SelectedLineCount));
        }
    }

    public string? SelectedPath => SelectedDocument is { IsSettings: false, IsPage: false } document ? document.FilePath : null;

    public string SelectedLanguage => SelectedDocument?.Language ?? string.Empty;

    public string SelectedLineCount
    {
        get
        {
            var text = SelectedDocument?.Text;
            if (text is null) return string.Empty;
            var lines = 1;
            foreach (var ch in text)
                if (ch == '\n') lines++;
            return $"{lines} lines";
        }
    }

    public bool IsSideBarVisible
    {
        get => _isSideBarVisible;
        set
        {
            if (_isSideBarVisible == value) return;
            _isSideBarVisible = value;
            OnPropertyChanged();
        }
    }

    public double SideBarWidth
    {
        get => _sideBarWidth;
        set
        {
            if (Math.Abs(_sideBarWidth - value) < 0.5) return;
            _sideBarWidth = value;
            OnPropertyChanged();
        }
    }

    public string StatusMessage
    {
        get => _statusMessage;
        set
        {
            if (_statusMessage == value) return;
            _statusMessage = value;
            OnPropertyChanged();
        }
    }

    public string? FolderPath
    {
        get => _folderPath;
        private set
        {
            if (_folderPath == value) return;
            _folderPath = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(FolderName));
            OnPropertyChanged(nameof(HasFolder));
            OnPropertyChanged(nameof(WindowTitle));
        }
    }

    public string FolderName => string.IsNullOrEmpty(FolderPath)
        ? "No folder opened"
        : Path.GetFileName(FolderPath.TrimEnd(Path.DirectorySeparatorChar));

    public bool HasFolder => FolderPath is not null;

    public string WindowTitle => FolderPath is null
        ? "Local Book Binder"
        : $"{FolderName} - Local Book Binder";

    public bool HasDocuments => Documents.Count > 0;

    public string ActiveActivity
    {
        get => _activeActivity;
        private set
        {
            if (_activeActivity == value) return;
            _activeActivity = value;
            OnPropertyChanged();
        }
    }

    public void OpenFolder()
    {
        var dialog = new OpenFolderDialog
        {
            Title = "Open Folder",
            Multiselect = false
        };

        if (dialog.ShowDialog() == true)
            LoadFolder(dialog.FolderName);
    }

    public void LoadFolder(string path)
    {
        if (!Directory.Exists(path)) return;

        FolderPath = path;
        Roots.Clear();

        var root = new ExplorerNode(path, isDirectory: true)
        {
            IsExpanded = true
        };
        root.EnsureChildren();
        Roots.Add(root);

        ActiveActivity = "Explorer";
        IsSideBarVisible = true;
        StatusMessage = $"Opened folder {path}";
        WatchFolder(path);
    }

    public void OpenSettings()
    {
        var existing = Documents.FirstOrDefault(document => document.IsSettings);
        if (existing is not null)
        {
            SelectedDocument = existing;
            StatusMessage = "Settings";
            return;
        }

        var tab = DocumentTab.CreateSettings();
        Documents.Add(tab);
        SelectedDocument = tab;
        OnPropertyChanged(nameof(HasDocuments));
        StatusMessage = "Settings";
    }

    public void RefreshExplorer()
    {
        if (Roots.Count == 0) return;

        Roots[0].Refresh();
        StatusMessage = "Explorer refreshed";
    }

    /// <summary>Opens <paramref name="page"/> in a tab, reusing the tab already showing the same key.</summary>
    public DocumentTab OpenPage(string title, string glyph, object page, string? key = null)
    {
        if (key is not null)
        {
            var existing = Documents.FirstOrDefault(document =>
                document.IsPage && string.Equals(document.PageKey, key, StringComparison.Ordinal));
            if (existing is not null)
            {
                SelectedDocument = existing;
                StatusMessage = existing.Title;
                return existing;
            }
        }

        var tab = DocumentTab.CreatePage(title, glyph, page, key);
        Documents.Add(tab);
        SelectedDocument = tab;
        OnPropertyChanged(nameof(HasDocuments));
        StatusMessage = title;
        return tab;
    }

    public void ClosePage(object page)
    {
        var tab = Documents.FirstOrDefault(document => ReferenceEquals(document.Page, page));
        if (tab is not null)
            CloseDocument(tab);
    }

    public void UpdatePageTitle(object page, string title)
    {
        var tab = Documents.FirstOrDefault(document => ReferenceEquals(document.Page, page));
        tab?.SetTitle(title);
    }

    public void ApplyState(AppState state)
    {
        IsSideBarVisible = state.IsSideBarVisible;
        SideBarWidth = state.SideBarWidth;
    }

    private void WatchFolder(string path)
    {
        _watcher?.Dispose();
        _watcher = null;

        try
        {
            _watcher = new FileSystemWatcher(path)
            {
                IncludeSubdirectories = true,
                NotifyFilter = NotifyFilters.FileName
                    | NotifyFilters.DirectoryName
                    | NotifyFilters.LastWrite
                    | NotifyFilters.Size,
                EnableRaisingEvents = true
            };

            _watcher.Created += OnFolderChanged;
            _watcher.Deleted += OnFolderChanged;
            _watcher.Renamed += OnFolderChanged;
            _watcher.Changed += OnFolderChanged;
        }
        catch (Exception ex) when (ex is IOException or ArgumentException or UnauthorizedAccessException)
        {
            _watcher = null;
        }
    }

    private void OnFolderChanged(object sender, FileSystemEventArgs e)
    {
        var dispatcher = Application.Current?.Dispatcher;
        if (dispatcher is null) return;

        dispatcher.BeginInvoke(() =>
        {
            if (_refreshTimer is null)
            {
                _refreshTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(600) };
                _refreshTimer.Tick += (_, _) =>
                {
                    _refreshTimer!.Stop();
                    RefreshExplorer();
                };
            }

            _refreshTimer.Stop();
            _refreshTimer.Start();
        });
    }

    public void OpenFile()
    {
        var dialog = new OpenFileDialog
        {
            Title = "Open File",
            Filter = "All files (*.*)|*.*"
        };

        if (dialog.ShowDialog() == true)
            OpenDocument(dialog.FileName);
    }

    public void OpenDocument(string path)
    {
        var existing = Documents.FirstOrDefault(d => string.Equals(d.FilePath, path, StringComparison.OrdinalIgnoreCase));
        if (existing is not null)
        {
            SelectedDocument = existing;
            StatusMessage = $"Activated {existing.Title}";
            return;
        }

        var tab = CreateTab(path);
        Documents.Add(tab);
        SelectedDocument = tab;
        OnPropertyChanged(nameof(HasDocuments));
        StatusMessage = $"Opened {tab.Title}";
    }

    public void CloseDocument(DocumentTab? tab)
    {
        if (tab is null || !Documents.Contains(tab)) return;

        var index = Documents.IndexOf(tab);
        Documents.Remove(tab);

        if (ReferenceEquals(SelectedDocument, tab))
            SelectedDocument = Documents.Count == 0
                ? null
                : Documents[Math.Min(index, Documents.Count - 1)];

        OnPropertyChanged(nameof(HasDocuments));
        StatusMessage = $"Closed {tab.Title}";
    }

    private void CloseAllDocuments()
    {
        Documents.Clear();
        SelectedDocument = null;
        OnPropertyChanged(nameof(HasDocuments));
        StatusMessage = "All tabs closed";
    }

    private void ShowExplorer()
    {
        ActiveActivity = "Explorer";
        IsSideBarVisible = true;
    }

    private void ShowAbout()
        => MessageBox.Show(
            "Local Book Binder\nA local-first document workspace.",
            "About Local Book Binder",
            MessageBoxButton.OK,
            MessageBoxImage.Information);

    private static DocumentTab CreateTab(string path)
    {
        var tab = new DocumentTab(path);

        try
        {
            var info = new FileInfo(path);
            if (!info.Exists)
                return tab;

            if (!TextExtensions.Contains(info.Extension) && !TextExtensions.Contains(info.Name))
                return tab;

            if (info.Length > MaxPreviewBytes)
            {
                return new DocumentTab(path)
                {
                    Placeholder = $"File is too large to preview ({info.Length / 1024 / 1024} MB)."
                };
            }

            using var stream = File.OpenRead(path);
            var buffer = new byte[Math.Min(info.Length, 4096)];
            var read = stream.Read(buffer, 0, buffer.Length);
            if (Array.IndexOf(buffer, (byte)0, 0, read) >= 0)
                return tab;

            stream.Position = 0;
            using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
            tab.Text = reader.ReadToEnd();
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            // Keep the tab with a placeholder when the file cannot be read.
        }

        return tab;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>Raised when the user asks to list the books of the current folder.</summary>
    public event EventHandler? BookListRequested;

    private void ShowBookList() => BookListRequested?.Invoke(this, EventArgs.Empty);

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}
