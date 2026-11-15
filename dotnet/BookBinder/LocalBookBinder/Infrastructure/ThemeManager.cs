using System.Windows;
using System.Windows.Media;

namespace LocalBookBinder.Infrastructure;

public sealed class ThemeDefinition
{
    private static readonly BrushConverter Converter = new();

    public ThemeDefinition(
        string id,
        string displayName,
        bool isDark,
        string source,
        string previewBackground,
        string previewAccent,
        string previewForeground)
    {
        Id = id;
        DisplayName = displayName;
        IsDark = isDark;
        Source = source;
        PreviewBackground = Parse(previewBackground);
        PreviewAccent = Parse(previewAccent);
        PreviewForeground = Parse(previewForeground);
    }

    public string Id { get; }
    public string DisplayName { get; }
    public bool IsDark { get; }
    public string Source { get; }
    public Brush PreviewBackground { get; }
    public Brush PreviewAccent { get; }
    public Brush PreviewForeground { get; }

    private static Brush Parse(string hex) => (Brush)Converter.ConvertFromString(hex)!;
}

public static class ThemeManager
{
    private const string PalettePrefix = "/LocalBookBinder;component/Themes/Palette.";

    public static IReadOnlyList<ThemeDefinition> Themes { get; } = new List<ThemeDefinition>
    {
        new("Dark+", "Dark+ (default dark)", true, PalettePrefix + "Dark.xaml", "#1E1E1E", "#007ACC", "#CCCCCC"),
        new("Light+", "Light+ (default light)", false, PalettePrefix + "Light.xaml", "#FFFFFF", "#005FB8", "#333333"),
        new("Monokai", "Monokai", true, PalettePrefix + "Monokai.xaml", "#272822", "#F92672", "#F8F8F2"),
        new("Dracula", "Dracula", true, PalettePrefix + "Dracula.xaml", "#282A36", "#BD93F9", "#F8F8F2"),
        new("Solarized Dark", "Solarized Dark", true, PalettePrefix + "SolarizedDark.xaml", "#002B36", "#268BD2", "#839496"),
        new("Solarized Light", "Solarized Light", false, PalettePrefix + "SolarizedLight.xaml", "#FDF6E3", "#268BD2", "#657B83"),
        new("GitHub Light", "GitHub Light", false, PalettePrefix + "GitHubLight.xaml", "#FFFFFF", "#0969DA", "#24292F"),
        new("High Contrast", "High Contrast", true, PalettePrefix + "HighContrast.xaml", "#000000", "#1AEBFF", "#FFFFFF")
    }.AsReadOnly();

    public static ThemeDefinition Default => Themes[1];

    public static ThemeDefinition Current { get; private set; } = Default;

    public static event EventHandler? ThemeChanged;

    public static ThemeDefinition Get(string? id)
        => Themes.FirstOrDefault(t => string.Equals(t.Id, id, StringComparison.OrdinalIgnoreCase)) ?? Default;

    public static void Apply(ThemeDefinition theme)
    {
        var dictionaries = Application.Current?.Resources.MergedDictionaries;
        if (dictionaries is null)
        {
            Current = theme;
            return;
        }

        var palette = new ResourceDictionary { Source = new Uri(theme.Source, UriKind.Relative) };
        dictionaries.Add(palette);

        for (var i = dictionaries.Count - 1; i >= 0; i--)
        {
            if (ReferenceEquals(dictionaries[i], palette)) continue;

            var source = dictionaries[i].Source?.OriginalString;
            if (source is not null && source.Contains("Themes/Palette.", StringComparison.OrdinalIgnoreCase))
                dictionaries.RemoveAt(i);
        }
        Current = theme;
        ThemeChanged?.Invoke(null, EventArgs.Empty);
    }
}