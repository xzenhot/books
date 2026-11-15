using System.Windows;
using System.Windows.Controls;

namespace WriterWorker.Views
{
    /// <summary>
    /// Header shared by every book page: the title, who created the item and when, followed by a
    /// separator; the rest of the page is shown underneath.
    /// </summary>
    public partial class BookPageHeader : UserControl
    {
        public static readonly DependencyProperty TitleProperty = DependencyProperty.Register(
            nameof(Title),
            typeof(string),
            typeof(BookPageHeader),
            new PropertyMetadata(string.Empty));

        /// <summary>Kind of page shown: "Book List", "Book", "Chapter" or "Segment".</summary>
        public static readonly DependencyProperty WindowTitleProperty = DependencyProperty.Register(
            nameof(WindowTitle),
            typeof(string),
            typeof(BookPageHeader),
            new PropertyMetadata("Page"));

        public static readonly DependencyProperty CreatedByProperty = DependencyProperty.Register(
            nameof(CreatedBy),
            typeof(string),
            typeof(BookPageHeader),
            new PropertyMetadata(BookMeta.Unknown));

        public static readonly DependencyProperty CreatedOnProperty = DependencyProperty.Register(
            nameof(CreatedOn),
            typeof(string),
            typeof(BookPageHeader),
            new PropertyMetadata(BookMeta.Unknown));

        public BookPageHeader()
        {
            InitializeComponent();
        }

        public string Title
        {
            get => (string)GetValue(TitleProperty);
            set => SetValue(TitleProperty, value);
        }

        public string WindowTitle
        {
            get => (string)GetValue(WindowTitleProperty);
            set => SetValue(WindowTitleProperty, value);
        }

        public string CreatedBy
        {
            get => (string)GetValue(CreatedByProperty);
            set => SetValue(CreatedByProperty, value);
        }

        public string CreatedOn
        {
            get => (string)GetValue(CreatedOnProperty);
            set => SetValue(CreatedOnProperty, value);
        }
    }
}
