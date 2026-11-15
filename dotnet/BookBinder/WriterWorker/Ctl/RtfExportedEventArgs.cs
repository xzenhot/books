namespace WriterWorker.Ctl;

public sealed class RtfExportedEventArgs : EventArgs
{
    public RtfExportedEventArgs(string path) => Path = path;

    public string Path { get; }
}
