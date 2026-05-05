/**
 * Component for displaying charts from base64-encoded PNG data.
 */

interface ChartDisplayProps {
  base64Image: string;
  title?: string;
}

export default function ChartDisplay({ base64Image, title }: ChartDisplayProps) {
  // Convert base64 string to data URI if not already a URI
  const imageSrc = base64Image.startsWith('data:') 
    ? base64Image 
    : `data:image/png;base64,${base64Image}`;

  return (
    <div className="my-4">
      {title && <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>}
      <img
        src={imageSrc}
        alt={title || 'Chart'}
        className="max-w-full h-auto rounded-lg"
      />
    </div>
  );
}
