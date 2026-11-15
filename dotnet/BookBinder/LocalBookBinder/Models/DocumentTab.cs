using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;

namespace LocalBookBinder.Models;

public sealed class DocumentTab : INotifyPropertyChanged
{
    private bool _isDirty;
    private string? _text;
    private string _title;

    public DocumentTab(string filePath)
    {
        FilePath = filePath;
        _title = Path.GetFileName(filePath);
        Language = Languages.For(filePath);
        Glyph = FileGlyphs.For(filePath);
    }

    private DocumentTab()
    {
        FilePath = string.Empty;
        _title = "Settings";
        Language = string.Empty;
        Glyph = "\uE713";
        IsSettings = true;
    }

    private DocumentTab(string title, string glyph, object page, string? key)
    {
        FilePath = string.Empty;
        _title = title;
        Language = string.Empty;
        Glyph = glyph;
        Page = page;
        PageKey = key;
    }

    public static DocumentTab CreateSettings() => new();

    /// <summary>Creates a tab that hosts a page (for example one of the book browser pages).</summary>
    public static DocumentTab CreatePage(string title, string glyph, object page, string? key = null)
        => new(title, glyph, page, key);

    public bool IsSettings { get; }

    /// <summary>The page hosted by the tab; null for text, file and settings tabs.</summary>
    public object? Page { get; }

    public bool IsPage => Page is not null;

    /// <summary>Identity of the page, used to activate an already open page instead of duplicating it.</summary>
    public string? PageKey { get; }

    public string FilePath { get; }

    public string Title
    {
        get => _title;
        private set
        {
            if (_title == value) return;
            _title = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(DisplayTitle));
        }
    }

    public void SetTitle(string title) => Title = title;

    public string Language { get; }
    public string Glyph { get; }

    public override string ToString() => Title;

    public string? Text
    {
        get => _text;
        set
        {
            if (_text == value) return;
            _text = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(IsText));
        }
    }

    public bool IsText => _text is not null;

    public string Placeholder { get; init; } = "Preview is not available for this file type.";

    public bool IsDirty
    {
        get => _isDirty;
        set
        {
            if (_isDirty == value) return;
            _isDirty = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(DisplayTitle));
        }
    }

    public string DisplayTitle => IsDirty ? Title + " \u25CF" : Title;

    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

internal static class Languages
{
    private static readonly Dictionary<string, string> Map = new(StringComparer.OrdinalIgnoreCase)
    {
        [".cs"] = "C#",
        [".xaml"] = "XAML",
        [".xml"] = "XML",
        [".json"] = "JSON",
        [".md"] = "Markdown",
        [".txt"] = "Plain Text",
        [".csproj"] = "MSBuild",
        [".props"] = "MSBuild",
        [".targets"] = "MSBuild",
        [".sln"] = "Solution",
        [".yml"] = "YAML",
        [".yaml"] = "YAML",
        [".ps1"] = "PowerShell",
        [".html"] = "HTML",
        [".css"] = "CSS",
        [".js"] = "JavaScript",
        [".ts"] = "TypeScript",
        [".pdf"] = "PDF",
    };

    public static string For(string path)
        => Map.TryGetValue(Path.GetExtension(path), out var language) ? language : "Plain Text";
}
