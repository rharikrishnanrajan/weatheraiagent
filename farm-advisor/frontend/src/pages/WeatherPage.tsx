// ==============================================================================
// AgriPulse: Weather Dashboard Page Component
// ==============================================================================
// WHAT THIS FILE DOES:
// 1. Renders the live weather dashboard (current temperature, wind, humidity, rain).
// 2. Displays active agricultural hazard alerts (frost warnings, heatwaves, gales).
// 3. Embeds an interactive temperature and precipitation chart for the next 48 hours.
// 4. Shows a 7-day agronomic forecast cards with evapotranspiration (ET0) and rain odds.
// 5. Provides a search box to look up weather for any city or region worldwide.
// ==============================================================================

import { useState, useEffect } from 'react';
import {
  Search,
  MapPin,
  Thermometer,
  Droplets,
  Wind,
  Gauge,
  Calendar,
  CloudSun,
} from 'lucide-react';
import { useFarmStore } from '../store/useFarmStore';
import { WeatherCard } from '../components/WeatherCard';
import { WeatherAlertBanner } from '../components/WeatherAlertBanner';
import { TempPrecipChart } from '../components/TempPrecipChart';

export const WeatherPage = () => {
  // Access weather data and actions from the Zustand store
  const { weather, loadWeather, profile } = useFarmStore();
  const [searchLocation, setSearchLocation] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  // Load default weather on first visit if not already loaded
  useEffect(() => {
    if (!weather) {
      loadWeather();
    }
  }, [weather, loadWeather]);

  /**
   * Search weather for a custom location entered by the user.
   */
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchLocation.trim()) return;
    setIsSearching(true);
    await loadWeather({ place_name: searchLocation.trim() });
    setIsSearching(false);
  };

  /**
   * Reset the dashboard to the coordinates in the farmer's profile.
   */
  const handleResetToProfile = async () => {
    if (profile?.latitude && profile?.longitude) {
      setSearchLocation('');
      await loadWeather({ lat: profile.latitude, lon: profile.longitude });
    }
  };

  // Display loading spinner while data is being fetched
  if (!weather) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-stone-500">
        <div className="w-8 h-8 border-4 border-farm-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p>Loading live Open-Meteo meteorological data...</p>
      </div>
    );
  }

  const { current, daily, hourly, alerts, location } = weather;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* ---------------------------------------------------------------------- */}
      {/* HEADER BAR: Location Title & Search Field                              */}
      {/* ---------------------------------------------------------------------- */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-stone-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 text-stone-500 text-xs font-semibold uppercase tracking-wider mb-1">
            <MapPin className="w-3.5 h-3.5 text-farm-600" />
            <span>Active Forecast Location</span>
          </div>
          <h1 className="text-xl font-bold text-stone-900">{location.name}</h1>
          <p className="text-xs text-stone-500">
            Coordinates: {location.latitude.toFixed(4)}°N, {location.longitude.toFixed(4)}°E •
            Elevation: {location.elevation}m
          </p>
        </div>

        {/* Location Search Form */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search another city/location..."
              value={searchLocation}
              onChange={(e) => setSearchLocation(e.target.value)}
              className="text-xs pl-9 pr-3 py-2 bg-stone-50 border border-stone-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-farm-600 w-64"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="px-3 py-2 bg-farm-600 hover:bg-farm-700 text-white text-xs font-medium rounded-lg transition-colors"
          >
            {isSearching ? 'Searching...' : 'Search'}
          </button>
          {profile && (
            <button
              type="button"
              onClick={handleResetToProfile}
              className="px-3 py-2 bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-medium rounded-lg transition-colors"
              title="Reset to your saved farm profile location"
            >
              Reset to Farm
            </button>
          )}
        </form>
      </div>

      {/* ---------------------------------------------------------------------- */}
      {/* SEVERE WEATHER HAZARD ALERTS                                           */}
      {/* ---------------------------------------------------------------------- */}
      {alerts && alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((alert, idx) => (
            <WeatherAlertBanner key={idx} alert={alert} />
          ))}
        </div>
      )}

      {/* ---------------------------------------------------------------------- */}
      {/* CURRENT CONDITIONS METRIC CARDS                                        */}
      {/* ---------------------------------------------------------------------- */}
      <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {/* Temperature */}
        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center gap-3">
          <div className="p-3 rounded-lg bg-amber-50 text-amber-600">
            <Thermometer className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-stone-500 font-medium">Temperature</div>
            <div className="text-xl font-bold text-stone-900">{current.temperature_2m}°C</div>
            <div className="text-[11px] text-stone-400">
              Feels like {current.apparent_temperature}°C
            </div>
          </div>
        </div>

        {/* Relative Humidity */}
        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center gap-3">
          <div className="p-3 rounded-lg bg-blue-50 text-blue-600">
            <Droplets className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-stone-500 font-medium">Relative Humidity</div>
            <div className="text-xl font-bold text-stone-900">{current.relative_humidity_2m}%</div>
            <div className="text-[11px] text-stone-400">
              {current.relative_humidity_2m > 80 ? 'High disease pressure' : 'Normal range'}
            </div>
          </div>
        </div>

        {/* Wind Speed */}
        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center gap-3">
          <div className="p-3 rounded-lg bg-teal-50 text-teal-600">
            <Wind className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-stone-500 font-medium">Wind Speed</div>
            <div className="text-xl font-bold text-stone-900">{current.wind_speed_10m} km/h</div>
            <div className="text-[11px] text-stone-400">Gusts: {current.wind_gusts_10m} km/h</div>
          </div>
        </div>

        {/* Current Precipitation */}
        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center gap-3">
          <div className="p-3 rounded-lg bg-sky-50 text-sky-600">
            <Gauge className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-stone-500 font-medium">Precipitation</div>
            <div className="text-xl font-bold text-stone-900">{current.precipitation} mm</div>
            <div className="text-[11px] text-stone-400">{current.weather_description}</div>
          </div>
        </div>
      </div>

      {/* ---------------------------------------------------------------------- */}
      {/* 48-HOUR HOURLY TEMPERATURE & PRECIPITATION CHART                       */}
      {/* ---------------------------------------------------------------------- */}
      {hourly && hourly.length > 0 && (
        <div className="bg-white p-4 md:p-6 rounded-xl border border-stone-200 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <CloudSun className="w-5 h-5 text-farm-600" />
            <h2 className="text-base font-bold text-stone-900">
              Next 48-Hour Temperature & Rainfall Forecast
            </h2>
          </div>
          <TempPrecipChart hourlyData={hourly} />
        </div>
      )}

      {/* ---------------------------------------------------------------------- */}
      {/* 7-DAY DAILY AGRONOMIC FORECAST CARDS                                   */}
      {/* ---------------------------------------------------------------------- */}
      <div className="bg-white p-4 md:p-6 rounded-xl border border-stone-200 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-5 h-5 text-farm-600" />
          <h2 className="text-base font-bold text-stone-900">7-Day Agronomic Forecast</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {daily.map((day, idx) => (
            <WeatherCard key={idx} day={day} />
          ))}
        </div>
      </div>
    </div>
  );
};
