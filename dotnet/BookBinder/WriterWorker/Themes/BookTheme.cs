using System.Windows;
using System.Windows.Media;

namespace WriterWorker.Themes
{
    /// <summary>
    /// Adds light-theme fallbacks for the palette brushes the book pages use, so they still
    /// render when the host application does not provide LocalBookBinder's palette. Brushes the
    /// application already defines are left untouched, so the host theme keeps applying.
    /// </summary>
    public static class BookTheme
    {
        private static readonly (string Key, string Color)[] Fallbacks =
        [
            ("EditorBackgroundBrush", "#FFFFFF"),
            ("SideBarBrush", "#F3F3F3"),
            ("TabStripBrush", "#F3F3F3"),
            ("TabInactiveBrush", "#ECECEC"),
            ("InputBackgroundBrush", "#FFFFFF"),
            ("PanelBorderBrush", "#E5E5E5"),
            ("TextBrush", "#333333"),
            ("MutedTextBrush", "#6F6F6F"),
            ("AccentBrush", "#005FB8"),
            ("HoverBrush", "#E8E8E8"),
            ("SelectionBrush", "#ADD6FF"),
            ("IconBrush", "#424242"),
            ("LinkBrush", "#005FB8"),
            ("TabActiveForegroundBrush", "#1F1F1F"),
            ("PlaceholderGlyphBrush", "#C9C9C9"),
        ];

        public static void Ensure(FrameworkElement element)
        {
            ArgumentNullException.ThrowIfNull(element);

            foreach (var (key, color) in Fallbacks)
            {
                if (element.Resources.Contains(key) || IsProvidedByApplication(key))
                {
                    continue;
                }

                element.Resources[key] = new SolidColorBrush((Color)ColorConverter.ConvertFromString(color));
            }
        }

        private static bool IsProvidedByApplication(string key)
        {
            var resources = Application.Current?.Resources;
            return resources is not null && Contains(resources, key);
        }

        private static bool Contains(ResourceDictionary dictionary, object key)
        {
            if (dictionary.Contains(key))
            {
                return true;
            }

            foreach (var merged in dictionary.MergedDictionaries)
            {
                if (Contains(merged, key))
                {
                    return true;
                }
            }

            return false;
        }
    }
}
