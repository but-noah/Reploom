import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LogIn, UserPlus, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import useAuth, { getLoginUrl, getSignupUrl } from '@/lib/use-auth';
import { getWorkspaceSettings, updateWorkspaceSettings } from '@/lib/workspace-settings';
import { useToast } from '@/hooks/use-toast';

export default function SettingsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Use "default" workspace for now - can be made dynamic later
  const workspaceId = 'default';

  const { data: settings, isLoading } = useQuery({
    queryKey: ['workspace-settings', workspaceId],
    queryFn: () => getWorkspaceSettings(workspaceId),
    enabled: !!user,
  });

  const [toneLevel, setToneLevel] = useState(settings?.tone_level || 3);
  const [styleText, setStyleText] = useState(settings?.style_json?.brand_voice || '');
  const [blocklistText, setBlocklistText] = useState(settings?.blocklist_json.join('\n') || '');

  // Update local state when settings are loaded
  React.useEffect(() => {
    if (settings) {
      setToneLevel(settings.tone_level);
      setStyleText(settings.style_json?.brand_voice || '');
      setBlocklistText(settings.blocklist_json.join('\n'));
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: (updates: { tone_level?: number; style_json?: Record<string, string>; blocklist_json?: string[] }) =>
      updateWorkspaceSettings(workspaceId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-settings', workspaceId] });
      toast({
        title: 'Settings saved',
        description: 'Your workspace settings have been updated successfully.',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to update settings',
        variant: 'destructive',
      });
    },
  });

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] my-auto gap-4">
        <h2 className="text-xl">You are not logged in</h2>
        <div className="flex gap-4">
          <Button asChild variant="default" size="default">
            <a href={getLoginUrl()} className="flex items-center gap-2">
              <LogIn />
              <span>Login</span>
            </a>
          </Button>
          <Button asChild variant="default" size="default">
            <a href={getSignupUrl()} className="flex items-center gap-2">
              <UserPlus />
              <span>Sign up</span>
            </a>
          </Button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <p>Loading settings...</p>
      </div>
    );
  }

  const handleSaveVoice = () => {
    updateMutation.mutate({
      tone_level: toneLevel,
      style_json: { brand_voice: styleText },
    });
  };

  const handleSaveGuardrails = () => {
    const blocklist = blocklistText
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);

    updateMutation.mutate({
      blocklist_json: blocklist,
    });
  };

  const getToneLabelFromValue = (value: number): string => {
    const labels = ['Very Formal', 'Formal', 'Neutral', 'Casual', 'Very Casual'];
    return labels[value - 1] || 'Neutral';
  };

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-8">Workspace Settings</h1>

      <Tabs defaultValue="voice" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="voice">Brand Voice</TabsTrigger>
          <TabsTrigger value="guardrails">Guardrails</TabsTrigger>
        </TabsList>

        <TabsContent value="voice">
          <Card>
            <CardHeader>
              <CardTitle>Brand Voice Settings</CardTitle>
              <CardDescription>
                Configure the tone and style for draft generation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <Label htmlFor="tone-slider" className="text-base">
                  Tone Level: <span className="font-semibold">{getToneLabelFromValue(toneLevel)}</span>
                </Label>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted-foreground w-20">Very Formal</span>
                  <input
                    id="tone-slider"
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={toneLevel}
                    onChange={(e) => setToneLevel(Number(e.target.value))}
                    className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="text-sm text-muted-foreground w-20 text-right">Very Casual</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="style-text" className="text-base">
                  Brand Voice Guidelines
                </Label>
                <Textarea
                  id="style-text"
                  placeholder="Enter additional brand voice guidelines (e.g., 'professional yet approachable', 'use active voice', etc.)"
                  value={styleText}
                  onChange={(e) => setStyleText(e.target.value)}
                  rows={5}
                  className="resize-none"
                />
                <p className="text-sm text-muted-foreground">
                  These guidelines will help shape the style of generated drafts.
                </p>
              </div>

              <Button onClick={handleSaveVoice} disabled={updateMutation.isPending}>
                <Save className="mr-2 h-4 w-4" />
                {updateMutation.isPending ? 'Saving...' : 'Save Brand Voice'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="guardrails">
          <Card>
            <CardHeader>
              <CardTitle>Guardrails Settings</CardTitle>
              <CardDescription>
                Configure blocklisted phrases and claims that should never appear in drafts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="blocklist-text" className="text-base">
                  Blocklist (one phrase per line)
                </Label>
                <Textarea
                  id="blocklist-text"
                  placeholder="Enter phrases to block, one per line&#10;Example:&#10;free trial&#10;money back guarantee&#10;limited time offer"
                  value={blocklistText}
                  onChange={(e) => setBlocklistText(e.target.value)}
                  rows={10}
                  className="resize-none font-mono text-sm"
                />
                <p className="text-sm text-muted-foreground">
                  Any draft containing these phrases will be blocked. Limited to 100 phrases, each max 200 characters.
                </p>
              </div>

              <Button onClick={handleSaveGuardrails} disabled={updateMutation.isPending}>
                <Save className="mr-2 h-4 w-4" />
                {updateMutation.isPending ? 'Saving...' : 'Save Guardrails'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
