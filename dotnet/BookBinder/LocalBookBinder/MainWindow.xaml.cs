using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Threading;
using LocalBookBinder.Infrastructure;
using LocalBookBinder.Models;
using LocalBookBinder.ViewModels;
using WriterWorker.Controller;
using WriterWorker.Models;
using WriterWorker.Views;

namespace LocalBookBinder;

public partial class MainWindow : Window, IBookPageHost
{
    private readonly MainViewModel _viewModel;
    private readonly DispatcherTimer _clockTimer = new() { Interval = TimeSpan.FromSeconds(15) };
    private readonly AppState _state;
    private ExplorerNode? _contextNode;
    private string? _lastPageKey;

    public MainViewModel ViewModel => _viewModel;

    public MainWindow(bool restoreLastSession = true)
    {
        InitializeComponent();
        _viewModel = new MainViewModel();
        DataContext = _viewModel;

        _state = AppState.Load();
        ApplyState();
        if (restoreLastSession && _state.LastFolder is { } lastFolder)
            _viewModel.LoadFolder(lastFolder);
        if (restoreLastSession)
            RestoreLastPage();

        ClockText.Text = DateTime.Now.ToString("HH:mm");
        _clockTimer.Tick += (_, _) => ClockText.Text = DateTime.Now.ToString("HH:mm");
        _clockTimer.Start();

        _viewModel.PropertyChanged += ViewModel_PropertyChanged;
        _viewModel.BookListRequested += ViewModel_BookListRequested;
        ThemeManager.ThemeChanged += OnThemeChanged;
        Loaded += (_, _) => ApplyDarkTitleBar();
        Closing += (_, _) => SaveState();
        Closed += (_, _) =>
        {
            ThemeManager.ThemeChanged -= OnThemeChanged;
            _clockTimer.Stop();
        };
    }

    private void ApplyState()
    {
        _viewModel.ApplyState(_state);

        Width = _state.WindowWidth;
        Height = _state.WindowHeight;

        if (_state.WindowLeft is { } left
            && _state.WindowTop is { } top
            && IsOnScreen(left, top, _state.WindowWidth, _state.WindowHeight))
        {
            WindowStartupLocation = WindowStartupLocation.Manual;
            Left = left;
            Top = top;
        }

        if (_state.IsMaximized)
            WindowState = WindowState.Maximized;

        SideBarColumn.Width = _viewModel.IsSideBarVisible
            ? new GridLength(_viewModel.SideBarWidth)
            : new GridLength(0);
    }

    public void PersistState() => SaveState();

    private void SaveState()
    {
        _state.Theme = ThemeManager.Current.Id;
        _state.LastFolder = _viewModel.FolderPath;
        _state.LastPage = CurrentPageKey();
        _state.IsSideBarVisible = _viewModel.IsSideBarVisible;
        _state.SideBarWidth = _viewModel.SideBarWidth;
        _state.IsMaximized = WindowState == WindowState.Maximized;

        var bounds = WindowState == WindowState.Normal
            ? new Rect(Left, Top, Width, Height)
            : RestoreBounds;

        _state.WindowWidth = bounds.Width;
        _state.WindowHeight = bounds.Height;
        _state.WindowLeft = bounds.Left;
        _state.WindowTop = bounds.Top;

        _state.Save();
    }

    private static bool IsOnScreen(double left, double top, double width, double height)
    {
        var area = new Rect(
            SystemParameters.VirtualScreenLeft,
            SystemParameters.VirtualScreenTop,
            SystemParameters.VirtualScreenWidth,
            SystemParameters.VirtualScreenHeight);

        return area.IntersectsWith(new Rect(left, top, Math.Max(width, 120), Math.Max(height, 120)));
    }

    private void ViewModel_BookListRequested(object? sender, EventArgs e)
        => ShowBooksPage(_viewModel.FolderPath);

    private void ShowBooksPage(string? rootFolder)
        => OpenBookPage(BookGlyphs.BookList, $"books:{rootFolder}", new BookListPage(rootFolder, this));

    public void ShowPage(BookPageRequest request)
        => OpenBookPage(request.Glyph, request.Key, request.Content, request.Title);

    private DocumentTab OpenBookPage(string glyph, string? key, FrameworkElement page, string? title = null)
    {
        var tab = _viewModel.OpenPage(title ?? page.GetType().Name, glyph, page, key);
        if (page is IBookPage bookPage)
            _viewModel.UpdatePageTitle(page, bookPage.Title);
        if (key is not null && IsRestorablePageKey(key))
            _lastPageKey = key;
        return tab;
    }

    public void ClosePage(FrameworkElement page)
    {
        var closedKey = _viewModel.Documents.FirstOrDefault(document => ReferenceEquals(document.Page, page))?.PageKey;
        _viewModel.ClosePage(page);

        if (closedKey is not null && string.Equals(closedKey, _lastPageKey, StringComparison.Ordinal))
            _lastPageKey = CurrentPageKey(exclude: closedKey);
    }

    /// <summary>Reopens the book page that was active when the window was closed last time.</summary>
    private void RestoreLastPage()
    {
        if (_state.LastPage is not { } key || !IsRestorablePageKey(key))
            return;

        var separator = key.IndexOf(':');
        var kind = key[..separator];
        var folder = key[(separator + 1)..];
        if (string.IsNullOrWhiteSpace(folder) || !Directory.Exists(folder))
            return;

        try
        {
            switch (kind)
            {
                case "books":
                    ShowBooksPage(folder);
                    break;
                case "book":
                    OpenBookPage(BookGlyphs.Book, key, new BookPage(folder, this));
                    break;
                case "bookview":
                    OpenBookPage(BookGlyphs.Book, key, new BookViewPage(folder));
                    break;
                case "published":
                    OpenBookPage(BookGlyphs.Book, key, new BookViewPage(folder));
                    break;
            }
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException
            or InvalidOperationException or System.Text.Json.JsonException)
        {
            _viewModel.StatusMessage = $"Could not restore {kind} page: {exception.Message}";
        }
    }

    private static bool IsRestorablePageKey(string key)
        => key.StartsWith("book:", StringComparison.Ordinal)
        || key.StartsWith("bookview:", StringComparison.Ordinal)
        || key.StartsWith("published:", StringComparison.Ordinal)
        || key.StartsWith("books:", StringComparison.Ordinal);

    /// <summary>Key of the book page to restore: the selected tab when it is a book page, else the last one opened.</summary>
    private string? CurrentPageKey(string? exclude = null)
    {
        if (_viewModel.SelectedDocument?.PageKey is { } selected
            && IsRestorablePageKey(selected)
            && !string.Equals(selected, exclude, StringComparison.Ordinal))
        {
            return selected;
        }

        return _lastPageKey is { } key
            && !string.Equals(key, exclude, StringComparison.Ordinal)
            && _viewModel.Documents.Any(document => string.Equals(document.PageKey, key, StringComparison.Ordinal))
            ? key
            : null;
    }

    public void UpdatePageTitle(FrameworkElement page, string title)
        => _viewModel.UpdatePageTitle(page, title);

    private void ViewModel_PropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        if (e.PropertyName != nameof(MainViewModel.IsSideBarVisible)) return;

        SideBarColumn.Width = _viewModel.IsSideBarVisible
            ? new GridLength(_viewModel.SideBarWidth)
            : new GridLength(0);
    }

    private void ExplorerTree_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
    {
        if (e.NewValue is ExplorerNode { IsDirectory: false } node)
            _viewModel.OpenDocument(node.FullPath);
    }

    private void ExplorerTree_ItemExpanded(object sender, RoutedEventArgs e)
    {
        if (e.OriginalSource is TreeViewItem { DataContext: ExplorerNode node } && node.IsDirectory)
            node.EnsureChildren();
    }

    private void ExplorerTree_ContextMenuOpening(object sender, ContextMenuEventArgs e)
    {
        _contextNode = FindAncestor<TreeViewItem>(e.OriginalSource as DependencyObject)?.DataContext as ExplorerNode;

        if (_contextNode is not { IsDirectory: true })
        {
            _contextNode = null;
            e.Handled = true;
            return;
        }

        BindBookMenuItem.Header = $"Bind Book \"{_contextNode.Name}\"";
    }

    /// <summary>
    /// Binds the folder selected in the explorer: <see cref="BookParsers"/> picks the parser,
    /// resolves the folder (a published book folder opens its newest version, a backlog folder is
    /// read as a plan) and returns the book model the page binds.
    /// </summary>
    private void BindBook_Click(object sender, RoutedEventArgs e)
    {
        if (_contextNode is not { IsDirectory: true } node)
            return;

        var parser = BookParsers.For(node.FullPath);
        var bookFolder = parser?.Resolve(node.FullPath);
        if (parser is null || string.IsNullOrWhiteSpace(bookFolder))
        {
            _viewModel.StatusMessage = BookParsers.Describe(node.FullPath);
            return;
        }

        if (parser.Source == BookSource.Published)
        {
            _viewModel.StatusMessage = $"Binding published book {node.Name}";
            OpenBookPage(BookGlyphs.Book, $"published:{bookFolder}", new BookViewPage(bookFolder), node.Name);
            return;
        }

        _viewModel.StatusMessage = $"Binding book {node.Name}";
        OpenBookPage(BookGlyphs.Book, $"book:{bookFolder}", new BookPage(bookFolder, this), node.Name);
    }

    private void DocumentTabs_PreviewMouseDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ChangedButton != MouseButton.Middle) return;

        if (FindAncestor<TabItem>(e.OriginalSource as DependencyObject)?.DataContext is DocumentTab tab)
        {
            _viewModel.CloseDocument(tab);
            e.Handled = true;
        }
    }

    private void Window_DragOver(object sender, DragEventArgs e)
    {
        e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop)
            ? DragDropEffects.Copy
            : DragDropEffects.None;
        e.Handled = true;
    }

    private void Window_Drop(object sender, DragEventArgs e)
    {
        if (e.Data.GetData(DataFormats.FileDrop) is not string[] paths || paths.Length == 0) return;

        var path = paths[0];
        if (Directory.Exists(path))
            _viewModel.LoadFolder(path);
        else if (File.Exists(path))
            _viewModel.OpenDocument(path);

        e.Handled = true;
    }

    private static T? FindAncestor<T>(DependencyObject? source) where T : DependencyObject
    {
        while (source is not null)
        {
            if (source is T match) return match;
            source = source is Visual
                ? VisualTreeHelper.GetParent(source)
                : LogicalTreeHelper.GetParent(source);
        }

        return null;
    }

    private void OnThemeChanged(object? sender, EventArgs e) => ApplyDarkTitleBar();

    private void ApplyDarkTitleBar()
    {
        try
        {
            var handle = new WindowInteropHelper(this).Handle;
            if (handle == IntPtr.Zero) return;

            var enabled = ThemeManager.Current.IsDark ? 1 : 0;
            if (DwmSetWindowAttribute(handle, 20, ref enabled, sizeof(int)) != 0)
                DwmSetWindowAttribute(handle, 19, ref enabled, sizeof(int));
        }
        catch (DllNotFoundException)
        {
        }
        catch (EntryPointNotFoundException)
        {
        }
    }

    [DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attribute, ref int value, int size);
}
