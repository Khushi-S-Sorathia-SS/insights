/**
 * Stub component for displaying charts.
 * To be implemented in Phase 8.
 */

interface ChartDisplayProps {
  base64Image: string;
  title?: string;
}

export default function ChartDisplay({ base64Image, title }: ChartDisplayProps) {
  return (
    <div className="my-4">
      {title && <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>}
      <img
        src={base64Image}
        alt={title || 'Chart'}
        className="max-w-full h-auto rounded-lg"
      />
    </div>
  );
}
