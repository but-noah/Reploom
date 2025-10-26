import { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getReview, approveReview, rejectReview, requestEdit } from '../lib/reviews';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import { ArrowLeft, Check, X, Edit3, AlertTriangle, TrendingUp } from 'lucide-react';

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [editedHtml, setEditedHtml] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [rejectFeedback, setRejectFeedback] = useState('');

  const {
    data: review,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['review', id],
    queryFn: () => getReview(id!),
    enabled: !!id,
  });

  const approveMutation = useMutation({
    mutationFn: () => approveReview(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review', id] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      toast.success('Draft approved successfully');
      navigate('/inbox');
    },
    onError: (error: Error) => {
      toast.error('Failed to approve draft', {
        description: error.message,
      });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (feedback: string) => rejectReview(id!, { feedback }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review', id] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      toast.success('Draft rejected');
      setShowRejectDialog(false);
      navigate('/inbox');
    },
    onError: (error: Error) => {
      toast.error('Failed to reject draft', {
        description: error.message,
      });
    },
  });

  const editMutation = useMutation({
    mutationFn: (data: { draft_html: string; edit_notes?: string }) => requestEdit(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review', id] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      toast.success('Draft updated successfully');
      setIsEditing(false);
      setEditNotes('');
    },
    onError: (error: Error) => {
      toast.error('Failed to update draft', {
        description: error.message,
      });
    },
  });

  const handleStartEdit = () => {
    if (review) {
      setEditedHtml(review.draft_html);
      setIsEditing(true);
    }
  };

  const handleSaveEdit = () => {
    editMutation.mutate({
      draft_html: editedHtml,
      edit_notes: editNotes || undefined,
    });
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedHtml('');
    setEditNotes('');
  };

  const handleReject = () => {
    rejectMutation.mutate(rejectFeedback);
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center py-12 text-muted-foreground">Loading review...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center py-12 text-destructive">
          Error loading review: {error.message}
        </div>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center py-12 text-muted-foreground">Review not found</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-6">
        <Button variant="ghost" onClick={() => navigate('/inbox')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Inbox
        </Button>
      </div>

      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Review Draft</h1>
            <p className="text-muted-foreground">Thread: {review.thread_id}</p>
          </div>
          <div className="flex gap-2">
            <Badge variant="secondary">Version {review.draft_version}</Badge>
            <Badge
              variant={
                review.status === 'approved'
                  ? 'success'
                  : review.status === 'rejected'
                    ? 'destructive'
                    : 'warning'
              }
            >
              {review.status}
            </Badge>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="p-4 border rounded-lg">
          <div className="text-sm text-muted-foreground mb-1">Intent</div>
          <div className="font-medium">
            {review.intent ? <Badge variant="info">{review.intent}</Badge> : 'N/A'}
          </div>
        </div>
        <div className="p-4 border rounded-lg">
          <div className="text-sm text-muted-foreground mb-1">Confidence</div>
          <div className="font-medium flex items-center gap-2">
            {review.confidence ? (
              <>
                <TrendingUp className="h-4 w-4" />
                {(review.confidence * 100).toFixed(0)}%
              </>
            ) : (
              'N/A'
            )}
          </div>
        </div>
        <div className="p-4 border rounded-lg">
          <div className="text-sm text-muted-foreground mb-1">Violations</div>
          <div className="font-medium">
            {review.violations.length > 0 ? (
              <span className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-4 w-4" />
                {review.violations.length}
              </span>
            ) : (
              <span className="text-green-600">None</span>
            )}
          </div>
        </div>
      </div>

      {review.violations.length > 0 && (
        <div className="mb-6 p-4 border border-destructive rounded-lg bg-destructive/10">
          <div className="font-semibold mb-2 text-destructive flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Policy Violations
          </div>
          <ul className="list-disc list-inside space-y-1">
            {review.violations.map((violation, idx) => (
              <li key={idx} className="text-sm">
                {violation}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Original Message</h2>
          <div className="prose prose-sm max-w-none">
            <p className="text-muted-foreground">
              {review.original_message_excerpt || review.original_message_summary}
            </p>
          </div>
        </div>

        <div className="border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Draft Response</h2>
            {!isEditing && review.status === 'pending' && (
              <Button variant="outline" size="sm" onClick={handleStartEdit}>
                <Edit3 className="mr-2 h-4 w-4" />
                Edit
              </Button>
            )}
          </div>

          {isEditing ? (
            <div className="space-y-4">
              <Textarea
                value={editedHtml}
                onChange={e => setEditedHtml(e.target.value)}
                className="min-h-[300px] font-mono text-sm"
                placeholder="Edit draft HTML..."
              />
              <Textarea
                value={editNotes}
                onChange={e => setEditNotes(e.target.value)}
                className="min-h-[100px]"
                placeholder="Add notes about your changes..."
              />
              <div className="flex gap-2">
                <Button onClick={handleSaveEdit} disabled={editMutation.isPending}>
                  {editMutation.isPending ? 'Saving...' : 'Save Changes'}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleCancelEdit}
                  disabled={editMutation.isPending}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: review.draft_html }}
            />
          )}
        </div>
      </div>

      {review.edit_notes && (
        <div className="mb-6 p-4 border rounded-lg bg-muted/50">
          <div className="font-semibold mb-2">Edit Notes</div>
          <p className="text-sm text-muted-foreground">{review.edit_notes}</p>
        </div>
      )}

      {review.status === 'pending' && !isEditing && (
        <div className="flex gap-4">
          <Button
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending || review.violations.length > 0}
            className="flex-1"
          >
            <Check className="mr-2 h-4 w-4" />
            {approveMutation.isPending ? 'Approving...' : 'Approve'}
          </Button>
          <Button
            variant="destructive"
            onClick={() => setShowRejectDialog(true)}
            disabled={rejectMutation.isPending}
            className="flex-1"
          >
            <X className="mr-2 h-4 w-4" />
            Reject
          </Button>
        </div>
      )}

      {review.status === 'approved' && (
        <div className="p-4 border border-green-500 rounded-lg bg-green-50 dark:bg-green-950">
          <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
            <Check className="h-5 w-5" />
            <span className="font-semibold">Draft Approved</span>
          </div>
          <p className="text-sm text-green-600 dark:text-green-500 mt-1">
            This draft has been approved and is ready to send.
          </p>
        </div>
      )}

      {review.status === 'rejected' && (
        <div className="p-4 border border-destructive rounded-lg bg-destructive/10">
          <div className="flex items-center gap-2 text-destructive">
            <X className="h-5 w-5" />
            <span className="font-semibold">Draft Rejected</span>
          </div>
          {review.feedback && (
            <p className="text-sm text-muted-foreground mt-2">Feedback: {review.feedback}</p>
          )}
        </div>
      )}

      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Draft</DialogTitle>
            <DialogDescription>
              Please provide feedback on why this draft is being rejected.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={rejectFeedback}
            onChange={e => setRejectFeedback(e.target.value)}
            placeholder="Enter your feedback..."
            className="min-h-[100px]"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={rejectMutation.isPending}
            >
              {rejectMutation.isPending ? 'Rejecting...' : 'Reject Draft'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
