using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using LocalBookBinder.Infrastructure;

namespace LocalBookBinder.ViewModels;

public sealed class SettingsViewModel : INotifyPropertyChanged
{
    private static readonly string[] Keywords =
    {
        "theme", "color theme", "colour theme", "appearance", "palette", "preset", "dark", "light"
    };

    private string _searchText = string.Empty;

    public SettingsViewModel()
    {
        ThemeOptions = new ObservableCollection<ThemeOption>(
            ThemeManager.Themes.Select(theme => new ThemeOption(theme, SelectTheme)));
        FilteredThemes = new ObservableCollection<ThemeOption>(ThemeOptions);

        SyncActiveTheme();
        ThemeManager.ThemeChanged += (_, _) => SyncActiveTheme();
    }

    public ObservableCollection<ThemeOption> ThemeOptions { get; }

    public ObservableCollection<ThemeOption> FilteredThemes { get; }

    public string SearchText
    {
        get => _searchText;
        set
        {
            var text = value ?? string.Empty;
            if (_searchText == text) return;
            _searchText = text;
            OnPropertyChanged();
            ApplyFilter();
        }
    }

    public string ActiveThemeName => ThemeManager.Current.DisplayName;

    public bool HasResults => FilteredThemes.Count > 0;

    public bool IsEmpty => FilteredThemes.Count == 0;

    public string ResultSummary => SearchText.Trim().Length == 0
        ? $"{ThemeOptions.Count} color themes"
        : $"{FilteredThemes.Count} of {ThemeOptions.Count} color themes";

    private static void SelectTheme(ThemeOption option) => ThemeManager.Apply(option.Definition);

    private void SyncActiveTheme()
    {
        foreach (var option in ThemeOptions)
            option.IsActive = ReferenceEquals(option.Definition, ThemeManager.Current);

        OnPropertyChanged(nameof(ActiveThemeName));
    }

    private void ApplyFilter()
    {
        var query = SearchText.Trim();

        FilteredThemes.Clear();
        foreach (var option in ThemeOptions)
        {
            if (query.Length == 0 || Matches(option, query))
                FilteredThemes.Add(option);
        }

        OnPropertyChanged(nameof(HasResults));
        OnPropertyChanged(nameof(IsEmpty));
        OnPropertyChanged(nameof(ResultSummary));
    }

    private static bool Matches(ThemeOption option, string query)
        => option.DisplayName.Contains(query, StringComparison.OrdinalIgnoreCase)
           || option.Kind.Contains(query, StringComparison.OrdinalIgnoreCase)
           || Keywords.Any(keyword => keyword.Contains(query, StringComparison.OrdinalIgnoreCase));

    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}