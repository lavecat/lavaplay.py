import typing as t
import asyncio
from .objects import Track, Filters, ConnectionInfo
from .exceptions import VolumeError
import random
if t.TYPE_CHECKING:
    from .node_manager import Node

class Player:
    def __init__(self, node: "Node", guild_id: int) -> None:
        self.guild_id = guild_id
        self.node = node
        self.rest = node.rest
        self._voice_state: t.Optional[dict] = None
        self.user_id: int = node.user_id
        self._voice_handlers: t.Dict[int, ConnectionInfo] = {}

        self._volume: int = 100
        self._filters: Filters = Filters()
        self.queue: t.List[Track] = []
        self.loop: asyncio.AbstractEventLoop = node.loop
        self._repeat = False
        self._queue_repeat = False
    

    def add_to_queue(self, tracks: t.List[Track], requester: t.Optional[int] = None) -> None:
        """
        Add tracks to queue. use to load a playlist result.

        >>> playlist = await lavaplayer.search_youtube("playlist url")
        >>> await lavaplayer.add_to_queue(guild_id, playlist.tracks)

        Parameters
        ---------
        tracks: :class:`list`
            tracks to add to queue
        """
        for track in tracks:
            self.loop.create_task(self.play(self.guild_id, track, requester))

    async def play(self, track: Track, requester: t.Optional[int] = None, start: int = 0) -> None:
        """
        Play track or add to the queue list.

        Parameters
        ---------
        requester: :class:`bool`
            user id for requester the play track
        start: :class:`bool`
            force play queue is ignored
        """
        if len(self.queue) == 0:
            await self.rest.update_player(
                session_id=self.node.session_id, 
                guild_id=self.guild_id,
                data={
                    "encodedTrack": track.track,
                    "position": 0 or start, 
                    "volume": 50
                }
            )
        track.requester = requester
        self.queue.append(track)

    def repeat(self, stats: bool) -> None:
        """
        Repeat the track for every.

        Parameters
        ---------
        stats: :class:`bool`
            the stats for repeat track
        """
        self._repeat = stats

    def queue_repeat(self, stats: bool) -> None:
        """
        Repeat the queue for every.

        Parameters
        ---------
        stats: :class:`bool`
            the stats for repeat queue
        """
        self._queue_repeat = stats
        self._repeat = False

    async def filters(self, filters: t.Optional[Filters]) -> None:
        """
        Repeat the track for every.

        Parameters
        ---------
        filters: :class:`Filters`
            add filters to the track
        """     
        if not filters:
            filters = Filters()
        filters._payload["guildId"] = str(self.guild_id)
        await self.rest.update_player(
            session_id=self.node.session_id,
            guild_id=self.guild_id,
            data={
                "filters": filters._payload
            }
        )

    async def stop(self) -> None:
        """
        Stop the track.
        """
        if len(self.queue) == 0:
            return
        self.queue.clear()
        await self.rest.update_player(
            session_id=self.node.session_id,
            guild_id=self.guild_id,
            data={
                "encodedTrack": None
            }
        )

    async def skip(self) -> None:
        """
        Skip the track
        """        
        if len(self.queue) == 0:
            return
        await self.rest.update_player(
            session_id=self.node.session_id,
            guild_id=self.guild_id,
            data={
                "encodedTrack": None
            }
        )

    async def pause(self, stats: bool) -> None:
        """
        Pause the track.

        Parameters
        ---------
        stats: :class:`bool`
            the stats for repeat track
        """        
        await self.rest.update_player(
            session_id=self.node.session_id,
            guild_id=self.guild_id,
            data={
                "paused": stats
            }
        )

    async def seek(self, position: int) -> None:
        """
        seek to custom position for the track, the position is in milliseconds.

        Parameters
        ---------
        position: :class:`int`
            the position is in milliseconds
        """        
        await self.rest.update_player(
            session_id=self.node.session_id,
            guild_id=self.guild_id,
            data={
                "position": position
            }
        )

    async def volume(self, volume: int) -> None:
        """
        Set volume for a player track.

        Parameters
        ---------
        volume: :class:`int`
            Volume may range from 0 to 1000. 100 is default

        Raises
        --------
        :exc:`.VolumeError`
            if volume is not in range from 0 to 1000.
        """
        if volume < 0 or volume > 1000:
            raise VolumeError("Volume may range from 0 to 1000. 100 is default", self.guild_id)        
        self._volume = volume
        await self.rest.update_player(
            session_id=self.node.session_id,
            guild_id=self.guild_id,
            data={
                "volume": volume
            }
        )

    async def destroy(self) -> None:
        """
        Tell the server to potentially disconnect from the voice server and potentially remove the player with all its data.
        This is useful if you want to move to a new node for a voice connection.
        Calling this function does not affect voice state, and you can send the same VOICE_SERVER_UPDATE to a new node.

        Parameters
        ---------

        Raises
        --------
        :exc:`.NodeError`
            If guild not found in nodes cache.
        """        
        await self.rest.destroy_player(self.node.session_id, self.guild_id)

    def shuffle(self, state: bool = True) -> t.Union["Node", t.List]:
        """
        Add shuffle to the track.

        Parameters
        ---------
        """        
        if not self.queue:
            return []
        self._shuffle = state
        np = self.queue[0]
        self.queue.remove(np)
        self.queue = random.sample(self.queue, len(self.queue))
        self.queue.insert(0, np)
        return self.queue

    def remove(self, position: int) -> None:
        """
        Remove a track from the queue.

        Parameters
        ---------
        position: :class:`int`
            the position of the track in the queue
        """        
        if not self.queue:
            return []
        self.queue.pop(position)
    
    def index(self, position: int) -> t.Union[Track, None]:
        """
        Get the track at a specific position in the queue.

        Parameters
        ---------
        position: :class:`int`
            the position of the track in the queue
        """        
        if not self.queue:
            return None
        elif position > len(self.queue):
            return None
        return self.queue[position]

    async def voice_update(self, session_id: str, token: str, endpoint: str, channel_id: t.Optional[int]) -> None:
        """
        Update the voice connection for a guild.

        Parameters
        ---------
        session_id: :class:`str`
            session id for connection
        token: :class:`str`
            token for connection
        endpoint: :class:`str`
            endpoint for connection
        channel_id: :class:`int`
            channel id for connection, if not give channel_id the connection will be closed
        """
        if not channel_id:
            await self.destroy(self.guild_id)
            return
        await self.rest.update_player(
            session_id=self.node.session_id,
            guild_id=self.guild_id,
            data={
                "voice": {
                    "token": token,
                    "sessionId": session_id,
                    "endpoint": endpoint.replace("wss://", "")
                }
            }
        )

    async def raw_voice_state_update(self, user_id: int, session_id: str, channel_id: t.Optional[int]) -> None:
        """
        A voice state update has been received from Discord.
        
        Parameters
        ---------
        user_id: :class:`int`
            user id
        session_id: :class:`str`
            session id
        channel_id: :class:`int` | :class:`None`
            the channel id, if not give the channel id will automatically destroy node.
        """
        if user_id != self.user_id:
            return
        elif not channel_id:
            await self.destroy(self.guild_id)
            return
        self._voice_handlers[self.guild_id] = ConnectionInfo(self.guild_id, session_id, channel_id)

    async def raw_voice_server_update(self, endpoint: str, token: str) -> None:
        """
        A voice server update has been received from Discord.
        
        Parameters
        ---------
        endpoint: :class:`str`
            the endpoint for the voice server
        token: :class:`str`
            the token for the voice server
        """
        connection_info = self._voice_handlers.get(self.guild_id)
        if not connection_info:
            return
        await self.voice_update(self.node.session_id, token, endpoint, connection_info.channel_id)

    async def wait_for_connection(self) -> t.Optional["Node"]:
        """
        Wait for the voice connection to be established.

        Parameters
        ---------
        """
        

    async def wait_for_remove_connection(self) -> None:
        """
        Wait for the voice connection to be removed.

        Parameters
        ---------

        Raises
        --------
        :exc:`.NodeError`
            If guild not found in nodes cache.
        """        
        
