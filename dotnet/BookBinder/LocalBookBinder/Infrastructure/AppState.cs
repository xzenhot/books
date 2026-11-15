using System.IO;
using System.Text.Json;
using WriterWorker.Ctl;

namespace LocalBookBinder.Infrastructure;

public sealed class AppState
{
    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };

    public string? LastFolder { get; set; }

    /// <summary>Key of the book page that was open last, e.g. <c>book:D:\...\pipeline\nouka</c>.</summary>
    public string? LastPage { get; set; }

    public string Theme { get; set; } = "Light+";
    public double WindowWidth { get; set; } = 1320;
    public double WindowHeight { get; set; } = 820;
    public double? WindowLeft { get; set; }
    public double? WindowTop { get; set; }
    public bool IsMaximized { get; set; }
    public bool IsSideBarVisible { get; set; } = true;
    public double SideBarWidth { get; set; } = 260;

    private static string FilePath => AppStorage.PathFor(AppStorage.StateFileName);

    public static AppState Load()
    {
        try
        {
            if (!File.Exists(FilePath)) return new AppState();
            var json = File.ReadAllText(FilePath);
            return JsonSerializer.Deserialize<AppState>(json) ?? new AppState();
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException)
        {
            return new AppState();
        }
    }

    public void Save()
    {
        try
        {
            var path = FilePath;
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(path, JsonSerializer.Serialize(this, Options));
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
        }
    }
}