using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;

namespace LocalBookBinder.Models;

public sealed class ExplorerNode : INotifyPropertyChanged
{
    private bool _isExpanded;
    private bool _childrenLoaded;

    public ExplorerNode(string fullPath, bool isDirectory)
    {
        FullPath = fullPath;
        IsDirectory = isDirectory;
        Name = isDirectory ? new DirectoryInfo(fullPath).Name : Path.GetFileName(fullPath);
        if (string.IsNullOrEmpty(Name))
            Name = fullPath;
    }

    public string Name { get; }

    public override string ToString() => Name;
    public string FullPath { get; }
    public bool IsDirectory { get; }
    public ObservableCollection<ExplorerNode> Children { get; } = new();

    public bool IsExpanded
    {
        get => _isExpanded;
        set
        {
            if (_isExpanded == value) return;
            _isExpanded = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(Glyph));
        }
    }

    public string Glyph => IsDirectory
        ? (IsExpanded ? "\uE838" : "\uE8B7")
        : FileGlyphs.For(FullPath);

    public void EnsureChildren()
    {
        if (_childrenLoaded || !IsDirectory) return;
        _childrenLoaded = true;

        try
        {
            var entries = new DirectoryInfo(FullPath)
                .EnumerateFileSystemInfos()
                .Where(e => (e.Attributes & FileAttributes.Hidden) == 0)
                .OrderByDescending(e => e is DirectoryInfo)
                .ThenBy(e => e.Name, StringComparer.OrdinalIgnoreCase);

            foreach (var entry in entries)
                Children.Add(new ExplorerNode(entry.FullName, entry is DirectoryInfo));
        }
        catch (UnauthorizedAccessException)
        {
            // Folders such as System Volume Information cannot be enumerated.
        }
        catch (IOException)
        {
        }
    }

    public void Refresh()
    {
        if (!IsDirectory) return;

        var expanded = Children
            .Where(child => child.IsDirectory && child.IsExpanded)
            .Select(child => child.FullPath)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        Children.Clear();
        _childrenLoaded = false;

        if (!IsExpanded && expanded.Count == 0) return;

        EnsureChildren();

        foreach (var child in Children)
        {
            if (child.IsDirectory && expanded.Contains(child.FullPath))
            {
                child.IsExpanded = true;
                child.Refresh();
            }
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

internal static class FileGlyphs
{
    private static readonly Dictionary<string, string> Map = new(StringComparer.OrdinalIgnoreCase)
    {
        [".pdf"] = "\uEA90",
        [".cs"] = "\uE943",
        [".xaml"] = "\uE943",
        [".json"] = "\uE9D5",
        [".xml"] = "\uE9D5",
        [".props"] = "\uE9D5",
        [".targets"] = "\uE9D5",
        [".csproj"] = "\uE9D5",
        [".sln"] = "\uE9D5",
        [".md"] = "\uE8A5",
        [".txt"] = "\uE8A5",
        [".png"] = "\uEB9F",
        [".jpg"] = "\uEB9F",
        [".jpeg"] = "\uEB9F",
        [".gif"] = "\uEB9F",
    };

    public static string For(string path)
        => Map.TryGetValue(Path.GetExtension(path), out var glyph) ? glyph : "\uE7C3";
}
