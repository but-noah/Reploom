import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { listReviews, type DraftReview } from '../lib/reviews';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Filter, RefreshCcw } from 'lucide-react';

const statusColors = {
  pending: 'warning',
  approved: 'success',
  rejected: 'destructive',
  editing: 'info',
} as const;

const intentColors = {
  support: 'info',
  cs: 'warning',
  exec: 'destructive',
  other: 'secondary',
} as const;

export default function InboxPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [intentFilter, setIntentFilter] = useState<string | undefined>();

  const {
    data: reviews,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['reviews', statusFilter, intentFilter],
    queryFn: () =>
      listReviews({
        status: statusFilter,
        intent: intentFilter,
      }),
  });

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const getConfidenceColor = (confidence: number | null) => {
    if (!confidence) return 'text-muted-foreground';
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Draft Review Inbox</h1>
        <p className="text-muted-foreground">Review and approve generated drafts before sending</p>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              Status: {statusFilter || 'All'}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => setStatusFilter(undefined)}>All</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setStatusFilter('pending')}>Pending</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setStatusFilter('approved')}>
              Approved
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setStatusFilter('rejected')}>
              Rejected
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setStatusFilter('editing')}>Editing</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              Intent: {intentFilter || 'All'}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => setIntentFilter(undefined)}>All</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setIntentFilter('support')}>Support</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setIntentFilter('cs')}>
              Customer Service
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setIntentFilter('exec')}>Executive</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setIntentFilter('other')}>Other</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button variant="ghost" onClick={() => refetch()}>
          <RefreshCcw className="h-4 w-4" />
        </Button>
      </div>

      {isLoading && (
        <div className="text-center py-12 text-muted-foreground">Loading reviews...</div>
      )}

      {error && (
        <div className="text-center py-12 text-destructive">
          Error loading reviews: {error.message}
        </div>
      )}

      {reviews && reviews.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          No reviews found. Generate a draft to get started.
        </div>
      )}

      {reviews && reviews.length > 0 && (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Thread</TableHead>
                <TableHead>Intent</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Violations</TableHead>
                <TableHead>Updated At</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reviews.map((review: DraftReview) => (
                <TableRow key={review.id}>
                  <TableCell className="max-w-md">
                    <div className="truncate font-medium">{review.original_message_summary}</div>
                    <div className="text-xs text-muted-foreground">
                      Thread: {review.thread_id.substring(0, 16)}...
                    </div>
                  </TableCell>
                  <TableCell>
                    {review.intent ? (
                      <Badge
                        variant={
                          intentColors[review.intent as keyof typeof intentColors] || 'secondary'
                        }
                      >
                        {review.intent}
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground text-xs">N/A</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {review.confidence ? (
                      <span className={`font-medium ${getConfidenceColor(review.confidence)}`}>
                        {(review.confidence * 100).toFixed(0)}%
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-xs">N/A</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusColors[review.status as keyof typeof statusColors]}>
                      {review.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {review.violations.length > 0 ? (
                      <Badge variant="destructive">{review.violations.length}</Badge>
                    ) : (
                      <span className="text-muted-foreground text-xs">None</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(review.updated_at)}
                  </TableCell>
                  <TableCell>
                    <Link to={`/review/${review.id}`}>
                      <Button variant="ghost" size="sm">
                        Review
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
