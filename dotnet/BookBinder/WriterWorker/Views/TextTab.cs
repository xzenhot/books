using System.Windows;
using System.Windows.Controls;

namespace WriterWorker.Views
{
    /// <summary>Builds the read-only text tabs used by the chapter and segment windows.</summary>
    internal static class TextTab
    {
        public static TabItem Create(FrameworkElement owner, string header, string? text, string? placeholder = null)
        {
            var body = string.IsNullOrWhiteSpace(text) ? placeholder ?? string.Empty : text;

            var box = new TextBox
            {
                Text = body,
                Style = owner.TryFindResource("BookTextStyle") as Style,
                IsReadOnly = true,
                AcceptsReturn = true,
                TextWrapping = TextWrapping.Wrap,
                VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            };

            return new TabItem { Header = header, Content = box };
        }
    }
}
