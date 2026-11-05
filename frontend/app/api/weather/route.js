export const runtime = "edge";

const LATITUDE = 36.84;
const LONGITUDE = 10.25;

export async function GET() {
  const params = new URLSearchParams({
    latitude: LATITUDE,
    longitude: LONGITUDE,
    hourly: [
      "temperature_2m",
      "wind_speed_10m",
      "wind_gusts_10m",
      "wind_direction_10m",
      "precipitation_probability",
      "precipitation",
      "weather_code",
    ].join(","),
    timezone: "Africa/Tunis",
    forecast_days: "3",
  });

  const response = await fetch(
    `https://api.open-meteo.com/v1/forecast?${params}`,
    {
      headers: { "User-Agent": "APT-Agent/1.0 (rowing assistant Lac de Tunis)" },
      next: { revalidate: 600 }, // cache 10 minutes on Vercel edge
    }
  );

  if (!response.ok) {
    return new Response(
      JSON.stringify({ error: "Weather fetch failed", status: response.status }),
      { status: response.status, headers: { "Content-Type": "application/json" } }
    );
  }

  const data = await response.json();
  return new Response(JSON.stringify(data), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "public, s-maxage=600",
    },
  });
}
