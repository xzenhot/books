namespace WriterWorker.Models
{
    /// <summary>
    /// A further reference printed with a chapter or a segment: the number it is cited by, the
    /// reference itself and the link to it when the source has one.
    /// </summary>
    public class BookReference
    {
        public string? Number { get; set; }

        public string? Text { get; set; }

        public string? WebLink { get; set; }
    }
}
