'use client';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
  AreaChart, Area, Radar, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ZAxis
} from 'recharts';
import { useState, useRef, useEffect } from 'react';
import { ChartSchema } from '../utils/api-client';

interface ChartDisplayProps {
  schema: ChartSchema;
}

const COLORS = ['#6366f1', '#0ea5e9', '#f43f5e', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];

// Generic Component Registry
const CHART_REGISTRY: Record<string, any> = {
  bar: { wrapper: BarChart, element: Bar, hasAxes: true },
  line: { wrapper: LineChart, element: Line, hasAxes: true },
  area: { wrapper: AreaChart, element: Area, hasAxes: true },
  scatter: { wrapper: ScatterChart, element: Scatter, hasAxes: true },
  pie: { wrapper: PieChart, element: Pie, hasAxes: false, isPolar: false },
  radar: { wrapper: RadarChart, element: Radar, hasAxes: false, isPolar: true }
};

export default function ChartDisplay({ schema }: ChartDisplayProps) {
  const [top, setTop] = useState(0);
  const [height, setHeight] = useState(300);
  const dragInfo = useRef<{ type: 'move' | 'resize', startY: number, initialTop: number, initialHeight: number, pointerId: number, target: HTMLElement } | null>(null);

  const startDrag = (e: React.PointerEvent, type: 'move' | 'resize') => {
    e.preventDefault();
    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);
    dragInfo.current = {
      type,
      startY: e.clientY,
      initialTop: top,
      initialHeight: height,
      pointerId: e.pointerId,
      target
    };
  };

  const handlePointerMove = (e: PointerEvent) => {
    if (!dragInfo.current) return;
    const deltaY = e.clientY - dragInfo.current.startY;
    if (dragInfo.current.type === 'move') {
      setTop(Math.max(0, dragInfo.current.initialTop + deltaY));
    } else {
      setHeight(Math.max(150, dragInfo.current.initialHeight + deltaY));
    }
  };

  const stopDrag = () => {
    if (!dragInfo.current) return;
    dragInfo.current.target.releasePointerCapture(dragInfo.current.pointerId);
    dragInfo.current = null;
  };

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => handlePointerMove(event);
    const onPointerUp = () => stopDrag();
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
  }, []);

  if (!schema || !schema.data || schema.data.length === 0) return null;

  const chartType = schema.type?.toLowerCase() || 'bar';

  // If the chart type isn't in our base registry, fallback to scatter (generic point rendering)
  const config = CHART_REGISTRY[chartType] || CHART_REGISTRY['scatter'];

  const WrapperComponent = config.wrapper;
  const DataComponent = config.element;

  const renderGenericChart = () => {
    // Coerce data values to numbers if they look like numbers
    const processedData = schema.data.map(item => {
      const newItem = { ...item };
      for (const k of Object.keys(newItem)) {
        if (typeof newItem[k] === 'string' && !isNaN(Number(newItem[k])) && newItem[k].trim() !== '') {
          newItem[k] = Number(newItem[k]);
        }
      }
      return newItem;
    });

    // Determine data keys based on schema or fallback defaults
    let xKey = schema.xAxis || 'x';
    let yKey = schema.yAxis || 'y';
    
    // Fallback heuristic if keys are missing in the data
    const dataKeys = Object.keys(processedData[0] || {});
    if (dataKeys.length > 0) {
      if (!dataKeys.includes(xKey)) xKey = dataKeys[0];
      if (!dataKeys.includes(yKey) && dataKeys.length > 1) {
         // Try to find a numeric key for Y
         const numericKey = dataKeys.find(k => typeof processedData[0][k] === 'number');
         yKey = numericKey || dataKeys[1];
      }
    }

    // Render for Cartesian coordinate charts (Bar, Line, Area, Scatter)
    if (config.hasAxes) {
      const isScatter = chartType === 'scatter';
      return (
        <ResponsiveContainer width="100%" height="100%">
          <WrapperComponent data={processedData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }} style={{ pointerEvents: 'none' }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey={xKey}
              type={isScatter ? 'number' : 'category'}
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              dy={10}
            />
            <YAxis
              dataKey={isScatter ? yKey : undefined}
              type="number"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#94a3b8', fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '12px' }}
              itemStyle={{ color: '#f8fafc', fontWeight: 'bold' }}
              cursor={isScatter ? { strokeDasharray: '3 3' } : undefined}
            />
            {/* Some DB schemas may define custom colors or properties, we pass them down if they exist */}
            <DataComponent
              dataKey={yKey}
              name={schema.title || yKey}
              fill={schema.fill || "#6366f1"}
              stroke={schema.stroke || "#6366f1"}
              radius={[6, 6, 0, 0]}
              {...(schema.extraProps || {})}
            >
              {processedData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </DataComponent>
          </WrapperComponent>
        </ResponsiveContainer>
      );
    }

    // Render for Polar coordinate charts (Radar)
    if (config.isPolar) {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <WrapperComponent data={processedData} style={{ pointerEvents: 'none' }}>
            <PolarGrid stroke="rgba(255,255,255,0.1)" />
            <PolarAngleAxis dataKey={xKey} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <PolarRadiusAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '12px' }}
              itemStyle={{ color: '#f8fafc', fontWeight: 'bold' }}
            />
            <DataComponent
              name={schema.title || yKey}
              dataKey={yKey}
              stroke="#6366f1"
              fill="#6366f1"
              fillOpacity={0.6}
              {...(schema.extraProps || {})}
            />
          </WrapperComponent>
        </ResponsiveContainer>
      );
    }

    // Render for Pie/Donut charts
    return (
      <ResponsiveContainer width="100%" height="100%">
        <WrapperComponent style={{ pointerEvents: 'none' }}>
          <DataComponent
            data={processedData}
            dataKey={yKey}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            innerRadius={schema.innerRadius || 70}
            outerRadius={schema.outerRadius || 100}
            paddingAngle={2}
            stroke="rgba(11, 19, 38, 0.8)"
            strokeWidth={2}
            {...(schema.extraProps || {})}
          >
            {processedData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </DataComponent>
          <Tooltip
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '12px' }}
            itemStyle={{ color: '#f8fafc', fontWeight: 'bold' }}
          />
          <Legend verticalAlign="bottom" iconType="circle" />
        </WrapperComponent>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="glass-card p-6 animate-fade-in border-t-2 border-t-indigo-500/30 absolute" style={{ top: `${top}px`, width: '100%', height: `${height}px` }}>
      <div onPointerDown={(e) => startDrag(e, 'move')} className="cursor-move p-2 bg-white/5 rounded-t-lg flex justify-center">
        <div className="w-6 h-1 bg-slate-400 rounded-full"></div>
      </div>
      {schema.title && (
        <div className="flex flex-col mb-6">
          <h3 className="text-sm font-black text-slate-100 uppercase tracking-widest">{schema.title}</h3>
          <div className="w-10 h-1 bg-gradient-to-r from-indigo-500 to-transparent mt-2 rounded-full"></div>
        </div>
      )}
      <div className="w-full" style={{ height: `${height - 120}px` }}>
        {renderGenericChart()}
      </div>
      <div onPointerDown={(e) => startDrag(e, 'resize')} className="cursor-ns-resize p-2 bg-white/5 rounded-b-lg flex justify-center absolute bottom-0 left-0 right-0">
        <div className="w-6 h-1 bg-slate-400 rounded-full"></div>
      </div>
    </div>
  );
}
