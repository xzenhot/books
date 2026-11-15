using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace WriterWorker.Parser.PublishedParser.Contents
{
    /// <summary>
    /// Reads the Markdown files of a published version. The publish step stamps every file it copies
    /// with a provenance block (<c>- **updated_by:**</c> / <c>- **updated_date:**</c>), placed under
    /// the title heading or at the top of the file; this strips that block, and the title heading,
    /// so the parser sees the same text the pipeline holds.
    /// </summary>
    internal static class PublishedMarkdown
    {
        private static readonly Regex StampLine = new(
            @"^-\s+\*\*(?:updated_by|updated_date|Updated by|Updated):\*\*",
            RegexOptions.IgnoreCase);

        /// <summary>
        /// Returns the text without front matter, title heading and stamp block. The heading itself is
        /// handed back through <paramref name="heading"/> because the caller needs it as a title.
        /// </summary>
        public static string? Read(string? text, out string? heading)
        {
            heading = null;
            if (string.IsNullOrWhiteSpace(text))
            {
                return text;
            }

            var newline = text.Contains("\r\n", StringComparison.Ordinal) ? "\r\n" : "\n";
            var lines = text.Split('\n').Select(line => line.TrimEnd('\r')).ToList();
            if (lines.Count > 0)
            {
                lines[0] = lines[0].TrimStart('\uFEFF');
            }

            var index = 0;

            // Optional YAML front matter.
            if (NextContent(lines, index) is { } frontStart && lines[frontStart].Trim() == "---")
            {
                var end = lines.FindIndex(frontStart + 1, line => line.Trim() == "---");
                if (end > 0)
                {
                    index = end + 1;
                }
            }

            // Title heading: only the first content line of the file counts as a title.
            if (NextContent(lines, index) is { } headingIndex && lines[headingIndex].StartsWith("# ", StringComparison.Ordinal))
            {
                heading = lines[headingIndex][2..].Trim();
                index = headingIndex + 1;
            }

            if (NextContent(lines, index) is { } blockStart)
            {
                index = blockStart;
                while (index < lines.Count && lines[index].StartsWith("- ", StringComparison.Ordinal))
                {
                    if (StampLine.IsMatch(lines[index]))
                    {
                        lines.RemoveAt(index);
                    }
                    else
                    {
                        index++;
                    }
                }
            }

            var body = string.Join(newline, lines);
            return body.Trim();
        }

        private static int? NextContent(List<string> lines, int from)
        {
            for (var index = from; index < lines.Count; index++)
            {
                if (!string.IsNullOrWhiteSpace(lines[index]))
                {
                    return index;
                }
            }

            return null;
        }
    }
}
