namespace WriterWorker.Models
{
    /// <summary>One saved snapshot of a segment text, shown as its own tab on the segment page.</summary>
    public class SegmentVersion
    {
        public int Version { get; set; }

        public string? Text { get; set; }
    }
}
