import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import type { WeatherDailyItem } from '../types';

interface Props {
  daily: WeatherDailyItem[];
}

export const TempPrecipChart = ({ daily }: Props) => {
  if (!daily || daily.length === 0) return null;

  const data = daily.map((d) => {
    const dObj = new Date(d.date);
    return {
      date: dObj.toLocaleDateString('en-US', { weekday: 'short', month: 'numeric', day: 'numeric' }),
      maxTemp: Math.round(d.temperature_2m_max),
      minTemp: Math.round(d.temperature_2m_min),
      rain: Number(d.precipitation_sum.toFixed(1)),
      rainProb: d.precipitation_probability_max ?? 0,
      et0: d.et0_fao_evapotranspiration ? Number(d.et0_fao_evapotranspiration.toFixed(1)) : 0,
    };
  });

  return (
    <div className="bg-white p-5 rounded-2xl border border-stone-200 shadow-xs">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
        <div>
          <h3 className="text-base font-bold text-stone-900">7-Day Agro-Weather Outlook</h3>
          <p className="text-xs text-stone-500">Max/Min Temperatures (°C) vs Rainfall Volume (mm)</p>
        </div>
        <div className="flex items-center space-x-3 text-xs">
          <span className="inline-flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-stone-600">Max Temp</span>
          </span>
          <span className="inline-flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
            <span className="text-stone-600">Min Temp</span>
          </span>
          <span className="inline-flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400" />
            <span className="text-stone-600">Rain (mm)</span>
          </span>
        </div>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis
              yAxisId="temp"
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={false}
              tickLine={false}
              unit="°"
            />
            <YAxis
              yAxisId="rain"
              orientation="right"
              tick={{ fontSize: 11, fill: '#0ea5e9' }}
              axisLine={false}
              tickLine={false}
              unit="mm"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#ffffff',
                borderRadius: '0.75rem',
                border: '1px solid #e2e8f0',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                fontSize: '12px',
              }}
            />
            <Bar yAxisId="rain" dataKey="rain" name="Rain (mm)" fill="#38bdf8" radius={[4, 4, 0, 0]} barSize={20} />
            <Line
              yAxisId="temp"
              type="monotone"
              dataKey="maxTemp"
              name="Max Temp (°C)"
              stroke="#f59e0b"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#f59e0b' }}
            />
            <Line
              yAxisId="temp"
              type="monotone"
              dataKey="minTemp"
              name="Min Temp (°C)"
              stroke="#3b82f6"
              strokeWidth={2.5}
              dot={{ r: 3, fill: '#3b82f6' }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
