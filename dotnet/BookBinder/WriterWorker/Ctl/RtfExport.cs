using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;

namespace WriterWorker.Ctl;

/// <summary>
/// Reads and writes <see cref="FlowDocument"/> content in the RTF format.
/// </summary>
public static class RtfExport
{
    public const string RtfFileFilter = "Rich Text Format (*.rtf)|*.rtf|All files (*.*)|*.*";

    public static void Save(RichTextBox editor, string path)
    {
        ArgumentNullException.ThrowIfNull(editor);
        Save(editor.Document, path);
    }

    public static void Save(FlowDocument document, string path)
    {
        ArgumentNullException.ThrowIfNull(document);
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        var fullPath = Path.GetFullPath(path);
        var directory = Path.GetDirectoryName(fullPath);
        if (!string.IsNullOrEmpty(directory))
            Directory.CreateDirectory(directory);

        var range = new TextRange(document.ContentStart, document.ContentEnd);
        using var stream = File.Create(fullPath);
        range.Save(stream, DataFormats.Rtf);
    }

    public static void Load(RichTextBox editor, string path)
    {
        ArgumentNullException.ThrowIfNull(editor);
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        var range = new TextRange(editor.Document.ContentStart, editor.Document.ContentEnd);
        using var stream = File.OpenRead(path);
        range.Load(stream, DataFormats.Rtf);
    }

    /// <summary>Reads a document from an RTF file, for rendering it without an editor.</summary>
    public static FlowDocument LoadDocument(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);

        var document = new FlowDocument();
        var range = new TextRange(document.ContentStart, document.ContentEnd);
        using var stream = File.OpenRead(path);
        range.Load(stream, DataFormats.Rtf);
        return document;
    }

    public static string ToRtf(FlowDocument document)
    {
        ArgumentNullException.ThrowIfNull(document);

        var range = new TextRange(document.ContentStart, document.ContentEnd);
        using var stream = new MemoryStream();
        range.Save(stream, DataFormats.Rtf);
        return Encoding.UTF8.GetString(stream.ToArray());
    }

    public static void FromRtf(RichTextBox editor, string rtf)
    {
        ArgumentNullException.ThrowIfNull(editor);
        ArgumentNullException.ThrowIfNull(rtf);

        var range = new TextRange(editor.Document.ContentStart, editor.Document.ContentEnd);
        using var stream = new MemoryStream(Encoding.UTF8.GetBytes(rtf));
        range.Load(stream, DataFormats.Rtf);
    }
}
