param(
    [string]$ThumbPath = "data/media/now_playing.jpg"
)

$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime -ErrorAction SilentlyContinue | Out-Null
    [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType=WindowsRuntime] | Out-Null
    [Windows.Storage.Streams.IRandomAccessStreamWithContentType, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null
    
    $asTaskMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { 
        $_.Name -eq 'AsTask' -and 
        $_.GetParameters().Count -eq 1 -and 
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
    } | Select-Object -First 1

    $async = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
    $mgrTask = $asTaskMethod.MakeGenericMethod([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]).Invoke($null, @($async))
    $mgrTask.Wait(1200) | Out-Null
    $mgr = $mgrTask.Result

    $session = $null
    if ($mgr) {
        $session = $mgr.GetCurrentSession()
        if (-not $session) {
            $sessions = $mgr.GetSessions()
            if ($sessions.Count -gt 0) { $session = $sessions[0] }
        }
    }

    if ($session) {
        $propsAsync = $session.TryGetMediaPropertiesAsync()
        $propsTask = $asTaskMethod.MakeGenericMethod([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties]).Invoke($null, @($propsAsync))
        $propsTask.Wait(1200) | Out-Null
        $props = $propsTask.Result

        $playback = $session.GetPlaybackInfo()
        $timeline = $session.GetTimelineProperties()

        $hasThumb = $false
        $thumbError = ""
        if ($props.Thumbnail) {
            try {
                $streamAsync = $props.Thumbnail.OpenReadAsync()
                $streamTask = $asTaskMethod.MakeGenericMethod([Windows.Storage.Streams.IRandomAccessStreamWithContentType]).Invoke($null, @($streamAsync))
                $streamTask.Wait()
                $stream = $streamTask.Result
                if ($stream -and $stream.Size -gt 0) {
                    $netStreamMethod = [System.IO.WindowsRuntimeStreamExtensions].GetMethods() | Where-Object {
                        $_.Name -eq 'AsStreamForRead' -and $_.GetParameters().Count -eq 1
                    } | Select-Object -First 1
                    $netStream = $netStreamMethod.Invoke($null, @($stream))

                    $fullPath = [System.IO.Path]::GetFullPath($ThumbPath)
                    $dir = [System.IO.Path]::GetDirectoryName($fullPath)
                    if ($dir -and -not (Test-Path $dir)) { [System.IO.Directory]::CreateDirectory($dir) | Out-Null }
                    
                    $fileStream = [System.IO.File]::Create($fullPath)
                    $netStream.CopyTo($fileStream)
                    $fileStream.Close()
                    $netStream.Close()
                    $hasThumb = (Test-Path $fullPath)
                }
            } catch {
                $thumbError = $_.Exception.Message
            }
        }

        $appId = $session.SourceAppUserModelId
        $appName = "Media"
        if ($appId -match "Spotify") { $appName = "Spotify" }
        elseif ($appId -match "Chrome") { $appName = "Chrome" }
        elseif ($appId -match "msedge") { $appName = "Edge" }
        elseif ($appId -match "AppleMusic") { $appName = "Apple Music" }

        [PSCustomObject]@{
            has_media = $true
            title = $props.Title
            artist = $props.Artist
            album = $props.AlbumTitle
            status = if ($playback) { $playback.PlaybackStatus.ToString() } else { "Playing" }
            app = $appName
            app_id = $appId
            position_ms = if ($timeline) { [int]($timeline.Position.TotalMilliseconds) } else { 0 }
            duration_ms = if ($timeline) { [int]($timeline.EndTime.TotalMilliseconds) } else { 0 }
            has_thumbnail = $hasThumb
            thumb_error = $thumbError
        } | ConvertTo-Json -Compress
        exit 0
    }
} catch {}

# Fallback: Check Spotify process directly
try {
    $spotify = Get-Process spotify -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle } | Select-Object -First 1
    if ($spotify -and $spotify.MainWindowTitle -and $spotify.MainWindowTitle -ne 'Spotify' -and $spotify.MainWindowTitle -ne 'Spotify Free' -and $spotify.MainWindowTitle -ne 'Spotify Premium') {
        $parts = $spotify.MainWindowTitle -split ' - ', 2
        $artist = if ($parts.Count -gt 1) { $parts[0] } else { '' }
        $title = if ($parts.Count -gt 1) { $parts[1] } else { $parts[0] }
        [PSCustomObject]@{
            has_media = $true
            title = $title
            artist = $artist
            album = ""
            status = "Playing"
            app = "Spotify"
            app_id = "Spotify.exe"
            position_ms = 0
            duration_ms = 0
            has_thumbnail = $false
        } | ConvertTo-Json -Compress
        exit 0
    }
} catch {}

[PSCustomObject]@{
    has_media = $false
    title = ""
    artist = ""
    album = ""
    status = "Stopped"
    app = ""
    app_id = ""
    position_ms = 0
    duration_ms = 0
    has_thumbnail = $false
} | ConvertTo-Json -Compress
