using System.IO;
using System.Windows;
using LocalBookBinder.Infrastructure;
using LocalBookBinder.ViewModels;

namespace LocalBookBinder;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        if (WriterWorker.Ctl.PageSetupHarness.TryRunFromEnvironment()) { Shutdown(); return; }

        var state = AppState.Load();
        ThemeManager.Apply(ThemeManager.Get(state.Theme));

        var window = new MainWindow(restoreLastSession: e.Args.Length == 0);
        MainWindow = window;
        window.Show();

        OpenStartupArgument(window.ViewModel, e.Args);
    }

    private static void OpenStartupArgument(MainViewModel viewModel, string[] args)
    {
        if (args.Length == 0) return;

        var path = Path.GetFullPath(args[0]);
        if (Directory.Exists(path))
            viewModel.LoadFolder(path);
        else if (File.Exists(path))
            viewModel.OpenDocument(path);
    }
}