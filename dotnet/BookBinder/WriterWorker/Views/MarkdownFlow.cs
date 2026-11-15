using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Documents;
using System.Windows.Media;

namespace WriterWorker.Views
{
    /// <summary>
    /// Converts the simple markdown produced by the book pipeline into a <see cref="FlowDocument"/>
    /// for the assembled-book reader: ATX headings (<c>#</c>, <c>##</c>, <c>###</c>), inline
    /// <c>*italic*</c> and <c>**bold**</c> spans, <c>-</c> bullet items and one paragraph per line
    /// (the pipeline writes one sentence per line, so blank lines separate verse paragraphs).
    /// </summary>
    public static class MarkdownFlow
    {
        /// <summary>Family the reader renders a book in when nothing else is asked for.</summary>
        public const string DefaultFontFamily = "Segoe UI";

        /// <summary>Reader font size in DIPs; 13 DIPs are 9.75 points on paper.</summary>
        public const double DefaultFontSize = 13;

        private static readonly Regex HeadingPattern = new(@"^(#{1,6})\s+(.*)$", RegexOptions.Compiled);
        private static readonly Regex BulletPattern = new(@"^\s*[-*]\s+(.*)$", RegexOptions.Compiled);

        public static FlowDocument Build(string? markdown, string fontFamily = DefaultFontFamily, double baseFontSize = DefaultFontSize)
        {
            var document = new FlowDocument
            {
                FontFamily = new FontFamily(fontFamily),
                FontSize = baseFontSize,
                PagePadding = new Thickness(14, 10, 14, 14),
            };

            if (string.IsNullOrWhiteSpace(markdown))
            {
                return document;
            }

            foreach (var rawLine in markdown.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n'))
            {
                var line = rawLine.TrimEnd();
                if (string.IsNullOrWhiteSpace(line))
                {
                    continue;
                }

                var heading = HeadingPattern.Match(line);
                if (heading.Success)
                {
                    document.Blocks.Add(CreateHeading(heading.Groups[2].Value.Trim(), heading.Groups[1].Value.Length, baseFontSize));
                    continue;
                }

                var bullet = BulletPattern.Match(line);
                if (bullet.Success)
                {
                    document.Blocks.Add(CreateParagraph(bullet.Groups[1].Value.Trim(), baseFontSize, bullet: true));
                    continue;
                }

                document.Blocks.Add(CreateParagraph(line, baseFontSize));
            }

            return document;
        }

        private static Paragraph CreateHeading(string text, int level, double baseFontSize)
        {
            var fontSize = level switch
            {
                <= 1 => baseFontSize + 9,
                2 => baseFontSize + 4,
                _ => baseFontSize + 2,
            };

            var paragraph = new Paragraph
            {
                Margin = level <= 1 ? new Thickness(0, 16, 0, 4) : new Thickness(0, 10, 0, 4),
                FontSize = fontSize,
                FontWeight = FontWeights.SemiBold,
                KeepWithNext = true,
            };

            AddInlines(paragraph, text);
            return paragraph;
        }

        private static Paragraph CreateParagraph(string text, double baseFontSize, bool bullet = false)
        {
            var paragraph = new Paragraph
            {
                FontSize = baseFontSize,
                Margin = bullet ? new Thickness(24, 0, 0, 2) : new Thickness(0, 0, 0, 4),
            };

            if (bullet)
            {
                paragraph.Inlines.Add(new Run("•  ") { FontSize = baseFontSize });
            }

            AddInlines(paragraph, text);
            return paragraph;
        }

        private static void AddInlines(Paragraph paragraph, string text)
        {
            var index = 0;
            while (index < text.Length)
            {
                if (text[index] != '*')
                {
                    var next = text.IndexOf('*', index);
                    if (next < 0)
                    {
                        next = text.Length;
                    }

                    paragraph.Inlines.Add(new Run(text.Substring(index, next - index)));
                    index = next;
                    continue;
                }

                if (index + 1 < text.Length && text[index + 1] == '*')
                {
                    var end = text.IndexOf("**", index + 2);
                    if (end > index + 2)
                    {
                        paragraph.Inlines.Add(new Run(text.Substring(index + 2, end - index - 2)) { FontWeight = FontWeights.Bold });
                        index = end + 2;
                        continue;
                    }
                }

                var italicEnd = text.IndexOf('*', index + 1);
                if (italicEnd > index + 1)
                {
                    paragraph.Inlines.Add(new Run(text.Substring(index + 1, italicEnd - index - 1)) { FontStyle = FontStyles.Italic });
                    index = italicEnd + 1;
                    continue;
                }

                paragraph.Inlines.Add(new Run("*"));
                index++;
            }
        }
    }
}
