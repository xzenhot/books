using System;
using System.IO;

namespace WriterWorker.Ctl;

/// <summary>
/// The one place that decides where the user's settings live. They are kept in a hidden
/// <c>.binder</c> folder inside the user profile - <c>~/.binder</c> - instead of the roaming
/// application data folder, so the last session, the saved layouts and the PDF setup sit next to
/// each other in a folder the user can find, copy or back up as a whole.
/// </summary>
public static class AppStorage
{
    /// <summary>Name of the settings folder inside the user profile.</summary>
    public const string FolderName = ".binder";

    /// <summary>Settings file of the main window (last folder, last page, window bounds, theme).</summary>
    public const string StateFileName = "state.json";

    /// <summary>Settings file of the named page layouts.</summary>
    public const string LayoutsFileName = "pdf-configurations.json";

    /// <summary>Settings file of the shared PDF setup.</summary>
    public const string PdfSetupFileName = "pdf-setup.json";

    private static string? _folder;

    /// <summary>The settings folder, created on first use. Falls back to the roaming application data folder when the profile cannot be resolved.</summary>
    public static string Folder => _folder ??= Prepare(ResolveFolder());

    /// <summary>Full path of <paramref name="fileName"/> inside <see cref="Folder"/>.</summary>
    public static string PathFor(string fileName) => Path.Combine(Folder, fileName);

    private static string ResolveFolder()
    {
        var profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

        return string.IsNullOrEmpty(profile)
            ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "LocalBookBinder")
            : Path.Combine(profile, FolderName);
    }

    private static string Prepare(string folder)
    {
        try
        {
            Directory.CreateDirectory(folder);
            MigrateFrom(LegacyFolder, folder);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or NotSupportedException)
        {
        }

        return folder;
    }

    /// <summary>Where earlier versions kept the settings, so they can be carried over once.</summary>
    private static string LegacyFolder => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "LocalBookBinder");

    /// <summary>Copies settings written by an earlier version when the new folder does not have them yet.</summary>
    private static void MigrateFrom(string source, string target)
    {
        if (string.IsNullOrEmpty(source) ||
            string.Equals(Path.GetFullPath(source), Path.GetFullPath(target), StringComparison.OrdinalIgnoreCase) ||
            !Directory.Exists(source))
        {
            return;
        }

        foreach (var name in new[] { StateFileName, LayoutsFileName, PdfSetupFileName })
        {
            var from = Path.Combine(source, name);
            var to = Path.Combine(target, name);

            try
            {
                if (File.Exists(from) && !File.Exists(to))
                {
                    File.Copy(from, to);
                }
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException or NotSupportedException)
            {
            }
        }
    }
}
