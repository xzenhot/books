using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace WriterWorker.Ctl;

/// <summary>
/// Index of the TrueType families installed on the machine, so a PDF export can turn a requested
/// family name into the name of an installed one.
/// <para>
/// The system and per-user font folders are indexed by reading the family/subfamily entries of
/// each font's <c>name</c> table, so every installed TrueType font - including the Bengali fonts
/// used by the writer pipeline - can be named in an export.
/// </para>
/// </summary>
public sealed class PdfFonts
{
    private const string Regular = "r";
    private const string Bold = "b";
    private const string Italic = "i";
    private const string BoldItalic = "bi";

    private static readonly string[] PreferredFamilies =
    {
        "Segoe UI", "Arial", "Tahoma", "Microsoft Sans Serif", "Times New Roman"
    };

    private static readonly string[] StyleSuffixes =
    {
        " semibold", " semilight", " light", " medium", " black", " bold", " italic", " oblique", " regular"
    };

    private static readonly object Gate = new();
    private static PdfFonts? _instance;

    private readonly Dictionary<string, FamilyEntry> _families = new(StringComparer.OrdinalIgnoreCase);

    private PdfFonts() => Index();

    /// <summary>The catalog shared by every export.</summary>
    public static PdfFonts Instance
    {
        get
        {
            lock (Gate)
            {
                return _instance ??= new PdfFonts();
            }
        }
    }

    /// <summary>Family used when a requested family is not installed.</summary>
    public static string FallbackFamily
    {
        get
        {
            var fonts = Instance;
            foreach (var candidate in PreferredFamilies)
            {
                var family = fonts.FindCanonical(candidate);
                if (family is not null)
                {
                    return family;
                }
            }

            return fonts._families.Keys.FirstOrDefault() ?? "Arial";
        }
    }

    /// <summary>Returns the installed family name matching <paramref name="familyName"/>, if any.</summary>
    public static string? FindFamily(string? familyName) => Instance.FindCanonical(familyName);

    /// <summary>Names of the installed TrueType families known to the catalog.</summary>
    public IReadOnlyList<string> FamilyNames => _families.Keys.OrderBy(name => name, StringComparer.OrdinalIgnoreCase).ToArray();

    private string? FindCanonical(string? familyName)
    {
        var name = Normalize(familyName);
        if (name.Length == 0)
        {
            return null;
        }

        var exact = _families.Keys.FirstOrDefault(key => string.Equals(key, name, StringComparison.OrdinalIgnoreCase));
        if (exact is not null)
        {
            return exact;
        }

        foreach (var suffix in StyleSuffixes)
        {
            if (!name.EndsWith(suffix, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var trimmed = name[..^suffix.Length].Trim();
            var match = _families.Keys.FirstOrDefault(key => string.Equals(key, trimmed, StringComparison.OrdinalIgnoreCase));
            if (match is not null)
            {
                return match;
            }
        }

        var first = name.Split(',')[0].Trim();
        return string.Equals(first, name, StringComparison.OrdinalIgnoreCase) ? null : FindCanonical(first);
    }

    private static string Normalize(string? familyName)
    {
        var name = familyName?.Trim() ?? string.Empty;
        if (name.StartsWith("./#", StringComparison.Ordinal))
        {
            name = name[3..];
        }

        if (name.StartsWith('#') || name.StartsWith('/'))
        {
            name = name[1..];
        }

        return name.Trim('"', '\'');
    }

    private void Index()
    {
        foreach (var folder in FontFolders())
        {
            IEnumerable<string> files;
            try
            {
                files = Directory.EnumerateFiles(folder, "*.ttf", SearchOption.TopDirectoryOnly).ToList();
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                continue;
            }

            foreach (var file in files)
            {
                var names = TrueTypeNameReader.Read(file);
                if (names is not { } value || string.IsNullOrWhiteSpace(value.Family) || string.IsNullOrWhiteSpace(value.Subfamily))
                {
                    continue;
                }

                if (!_families.TryGetValue(value.Family, out var entry))
                {
                    entry = new FamilyEntry(value.Family);
                    _families[value.Family] = entry;
                }

                var style = Classify(value.Subfamily);
                entry.Faces.TryAdd(style, file);
            }
        }

        // A family without a regular face cannot be used for body text.
        foreach (var name in _families.Where(pair => !pair.Value.Faces.ContainsKey(Regular)).Select(pair => pair.Key).ToList())
        {
            _families.Remove(name);
        }
    }

    private static string Classify(string subfamily)
    {
        var value = subfamily.ToLowerInvariant();
        var bold = value.Contains("bold", StringComparison.Ordinal);
        var italic = value.Contains("italic", StringComparison.Ordinal) || value.Contains("oblique", StringComparison.Ordinal);

        return bold && italic ? BoldItalic : bold ? Bold : italic ? Italic : Regular;
    }

    private static IEnumerable<string> FontFolders()
    {
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        if (!string.IsNullOrEmpty(local))
        {
            var userFonts = Path.Combine(local, "Microsoft", "Windows", "Fonts");
            if (Directory.Exists(userFonts))
            {
                yield return userFonts;
            }
        }

        var fonts = Environment.GetFolderPath(Environment.SpecialFolder.Fonts);
        if (string.IsNullOrEmpty(fonts))
        {
            fonts = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Fonts");
        }

        if (Directory.Exists(fonts))
        {
            yield return fonts;
        }
    }

    private sealed class FamilyEntry
    {
        public FamilyEntry(string name) => Name = name;

        public string Name { get; }

        public Dictionary<string, string> Faces { get; } = new(StringComparer.OrdinalIgnoreCase);
    }

    /// <summary>Reads the family and subfamily names out of a TrueType <c>name</c> table.</summary>
    private static class TrueTypeNameReader
    {
        private const uint TrueTypeCollectionTag = 0x74746366; // 'ttcf'
        private const uint NameTableTag = 0x6E616D65;          // 'name'
        private const int NameTableHeaderSize = 6;
        private const int NameRecordSize = 12;

        public static (string Family, string Subfamily)? Read(string path)
        {
            try
            {
                using var stream = File.OpenRead(path);

                var header = new byte[12];
                if (stream.Read(header, 0, header.Length) < header.Length)
                {
                    return null;
                }

                if (ReadUInt32(header, 0) == TrueTypeCollectionTag)
                {
                    // Font collections store one face per entry; they are left to the renderer.
                    return null;
                }

                var tableCount = ReadUInt16(header, 4);
                if (tableCount == 0)
                {
                    return null;
                }

                var directory = new byte[tableCount * 16];
                if (stream.Read(directory, 0, directory.Length) < directory.Length)
                {
                    return null;
                }

                for (var index = 0; index < tableCount; index++)
                {
                    var record = index * 16;
                    if (ReadUInt32(directory, record) != NameTableTag)
                    {
                        continue;
                    }

                    var offset = ReadUInt32(directory, record + 8);
                    var length = ReadUInt32(directory, record + 12);
                    if (length < NameTableHeaderSize || offset < 0 || offset + length > stream.Length)
                    {
                        return null;
                    }

                    var table = new byte[length];
                    stream.Position = offset;
                    return stream.Read(table, 0, table.Length) < table.Length ? null : Parse(table);
                }

                return null;
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                return null;
            }
        }

        private static (string Family, string Subfamily)? Parse(byte[] table)
        {
            var count = ReadUInt16(table, 2);
            var stringOffset = ReadUInt16(table, 4);
            string? family = null;
            string? subfamily = null;
            var familyScore = -1;
            var subfamilyScore = -1;

            for (var index = 0; index < count; index++)
            {
                var record = NameTableHeaderSize + index * NameRecordSize;
                if (record + NameRecordSize > table.Length)
                {
                    break;
                }

                var platform = ReadUInt16(table, record);
                var encoding = ReadUInt16(table, record + 2);
                var language = ReadUInt16(table, record + 4);
                var nameId = ReadUInt16(table, record + 6);
                var length = ReadUInt16(table, record + 8);
                var offset = ReadUInt16(table, record + 10);

                // Platform 0 is Unicode, platform 3 encoding 1/10 is Windows Unicode BMP/full.
                var isUnicode = platform == 0 || (platform == 3 && (encoding == 1 || encoding == 10));
                if (!isUnicode || (nameId != 1 && nameId != 2))
                {
                    continue;
                }

                var start = stringOffset + offset;
                if (length == 0 || start + length > table.Length)
                {
                    continue;
                }

                var text = Encoding.BigEndianUnicode.GetString(table, start, length).Trim('\0', ' ');
                if (text.Length == 0)
                {
                    continue;
                }

                // English (US) and language-neutral records carry the names other tools expect.
                var score = language switch
                {
                    0x0409 => 2,
                    0 => 1,
                    _ => 0
                };

                if (nameId == 1)
                {
                    if (score > familyScore)
                    {
                        family = text;
                        familyScore = score;
                    }
                }
                else if (score > subfamilyScore)
                {
                    subfamily = text;
                    subfamilyScore = score;
                }
            }

            return family is null || subfamily is null ? null : (family, subfamily);
        }

        private static int ReadUInt16(byte[] buffer, int offset)
            => offset + 1 < buffer.Length ? (buffer[offset] << 8) | buffer[offset + 1] : 0;

        private static int ReadUInt32(byte[] buffer, int offset)
            => offset + 3 < buffer.Length
                ? (buffer[offset] << 24) | (buffer[offset + 1] << 16) | (buffer[offset + 2] << 8) | buffer[offset + 3]
                : 0;
    }
}
