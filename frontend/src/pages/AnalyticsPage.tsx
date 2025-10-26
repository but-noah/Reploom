import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getAnalyticsSummary,
  formatDuration,
  calculatePercentageChange,
  formatPercentage,
  type AnalyticsSummary,
} from "../lib/analytics";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle2,
  XCircle,
  Edit3,
  AlertCircle,
  BarChart3,
} from "lucide-react";
import { Skeleton } from "../components/ui/skeleton";

export default function AnalyticsPage() {
  const [window, setWindow] = useState<"7d" | "30d">("7d");
  const [slaThreshold] = useState(300); // 5 minutes default

  const {
    data: analytics,
    isLoading,
    error,
  } = useQuery<AnalyticsSummary>({
    queryKey: ["analytics", window, slaThreshold],
    queryFn: () =>
      getAnalyticsSummary({
        window,
        sla_threshold_seconds: slaThreshold,
      }),
  });

  const renderTrendIndicator = (current: number, previous: number) => {
    const change = calculatePercentageChange(current, previous);
    const isPositive = change > 0;
    const Icon = isPositive ? TrendingUp : TrendingDown;
    const color = isPositive ? "text-green-600" : "text-red-600";

    if (Math.abs(change) < 0.1) {
      return (
        <span className="text-sm text-muted-foreground">No change</span>
      );
    }

    return (
      <div className={`flex items-center gap-1 text-sm ${color}`}>
        <Icon className="h-4 w-4" />
        <span>{formatPercentage(Math.abs(change), 1)}</span>
      </div>
    );
  };

  const renderIntentDistribution = () => {
    if (!analytics) return null;

    const intents = analytics.metrics.intents_count;
    const total = Object.values(intents).reduce((sum, count) => sum + count, 0);

    const intentColors: Record<string, string> = {
      support: "bg-blue-500",
      cs: "bg-green-500",
      exec: "bg-purple-500",
      other: "bg-gray-500",
      unknown: "bg-gray-400",
    };

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Entries by Intent
          </CardTitle>
        </CardHeader>
        <CardContent>
          {total === 0 ? (
            <p className="text-sm text-muted-foreground">No data available</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(intents)
                .sort(([, a], [, b]) => b - a)
                .map(([intent, count]) => {
                  const percentage = (count / total) * 100;
                  const previousCount =
                    analytics.trend.intents_count_previous[intent] || 0;

                  return (
                    <div key={intent} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div
                            className={`h-3 w-3 rounded-full ${
                              intentColors[intent] || "bg-gray-400"
                            }`}
                          />
                          <span className="capitalize">{intent}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-semibold">
                            {count} ({formatPercentage(percentage, 0)})
                          </span>
                          {renderTrendIndicator(count, previousCount)}
                        </div>
                      </div>
                      <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            intentColors[intent] || "bg-gray-400"
                          }`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              <div className="pt-2 border-t text-sm text-muted-foreground">
                Total entries: <span className="font-semibold">{total}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderReviewRate = () => {
    if (!analytics) return null;

    const { review_rate } = analytics.metrics;
    const { review_rate_previous } = analytics.trend;

    const statusItems = [
      {
        label: "Approved",
        count: review_rate.approved,
        rate: review_rate.approved_rate,
        previous: review_rate_previous.approved,
        icon: CheckCircle2,
        color: "text-green-600",
      },
      {
        label: "Rejected",
        count: review_rate.rejected,
        rate: review_rate.rejected_rate,
        previous: review_rate_previous.rejected,
        icon: XCircle,
        color: "text-red-600",
      },
      {
        label: "Editing",
        count: review_rate.editing,
        rate: review_rate.editing_rate,
        previous: review_rate_previous.editing,
        icon: Edit3,
        color: "text-yellow-600",
      },
      {
        label: "Pending",
        count: review_rate.pending,
        rate: review_rate.pending_rate,
        previous: review_rate_previous.pending,
        icon: AlertCircle,
        color: "text-gray-600",
      },
    ];

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" />
            Human Review Rate
          </CardTitle>
        </CardHeader>
        <CardContent>
          {review_rate.total === 0 ? (
            <p className="text-sm text-muted-foreground">No data available</p>
          ) : (
            <div className="space-y-4">
              {statusItems.map(({ label, count, rate, previous, icon: Icon, color }) => (
                <div key={label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className={`h-5 w-5 ${color}`} />
                    <span className="text-sm font-medium">{label}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="font-semibold">
                        {count} <span className="text-sm text-muted-foreground">({formatPercentage(rate, 1)})</span>
                      </div>
                    </div>
                    {renderTrendIndicator(count, previous)}
                  </div>
                </div>
              ))}
              <div className="pt-2 border-t">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Total reviews:</span>
                  <span className="font-semibold">{review_rate.total}</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderFRT = () => {
    if (!analytics) return null;

    const { frt } = analytics.metrics;
    const { frt_previous } = analytics.trend;

    const metrics = [
      {
        label: "Average FRT",
        value: formatDuration(frt.avg_seconds),
        previous: frt_previous.avg_seconds,
        current: frt.avg_seconds,
      },
      {
        label: "Median FRT",
        value: formatDuration(frt.median_seconds),
        previous: frt_previous.median_seconds,
        current: frt.median_seconds,
      },
      {
        label: "Min FRT",
        value: formatDuration(frt.min_seconds),
        previous: frt_previous.min_seconds,
        current: frt.min_seconds,
      },
      {
        label: "Max FRT",
        value: formatDuration(frt.max_seconds),
        previous: frt_previous.max_seconds,
        current: frt.max_seconds,
      },
    ];

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            First Response Time (FRT) & SLA
          </CardTitle>
        </CardHeader>
        <CardContent>
          {frt.total_with_frt === 0 ? (
            <p className="text-sm text-muted-foreground">No data available</p>
          ) : (
            <div className="space-y-4">
              {/* SLA Compliance */}
              <div className="p-4 bg-secondary rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">SLA Compliance</span>
                  <span className="text-2xl font-bold">
                    {formatPercentage(frt.sla_met_percentage, 1)}
                  </span>
                </div>
                <div className="h-2 w-full bg-background rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      frt.sla_met_percentage >= 80
                        ? "bg-green-500"
                        : frt.sla_met_percentage >= 60
                        ? "bg-yellow-500"
                        : "bg-red-500"
                    }`}
                    style={{ width: `${frt.sla_met_percentage}%` }}
                  />
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  {frt.sla_met_count} of {frt.total_with_frt} reviews met SLA
                  threshold ({formatDuration(frt.sla_threshold_seconds)})
                </div>
              </div>

              {/* FRT Metrics */}
              <div className="space-y-3">
                {metrics.map(({ label, value, previous, current }) => (
                  <div key={label} className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{label}</span>
                    <div className="flex items-center gap-3">
                      <span className="font-semibold">{value}</span>
                      {renderTrendIndicator(current, previous)}
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-2 border-t text-sm text-muted-foreground">
                Based on {frt.total_with_frt} reviewed entries
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
          <h3 className="font-semibold text-destructive">Error loading analytics</h3>
          <p className="text-sm text-muted-foreground mt-1">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics</h1>
          <p className="text-muted-foreground mt-1">
            Track your draft review metrics and performance
          </p>
        </div>

        {/* Window selector */}
        <div className="flex gap-2">
          <Button
            variant={window === "7d" ? "default" : "outline"}
            onClick={() => setWindow("7d")}
          >
            Last 7 Days
          </Button>
          <Button
            variant={window === "30d" ? "default" : "outline"}
            onClick={() => setWindow("30d")}
          >
            Last 30 Days
          </Button>
        </div>
      </div>

      {/* Period info */}
      {analytics && (
        <div className="text-sm text-muted-foreground">
          Period: {new Date(analytics.period_start).toLocaleDateString()} -{" "}
          {new Date(analytics.period_end).toLocaleDateString()}
        </div>
      )}

      {/* Metrics cards */}
      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-24 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {renderIntentDistribution()}
          {renderReviewRate()}
          {renderFRT()}
        </div>
      )}
    </div>
  );
}
