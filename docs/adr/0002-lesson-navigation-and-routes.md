# Give lessons browser-addressable routes

Represent each lesson as a distinct fragment URL in the offline player. Lesson
navigation adds browser history entries, so Back and Forward revisit lessons;
changing routes stops the old lesson's narration. Fragment routes preserve
direct offline use without a server or build step. The lesson list follows
course order, shows unavailable lessons as disabled, and previous/next lesson
controls stop at the course boundaries.

In the desktop app, lesson addresses are internal. Expose Back and Forward
within the app for the current session, independently of previous and next
lesson controls. For example, jumping from lesson 2 to lesson 7 makes Back
return to lesson 2 and Previous Lesson open lesson 6.
