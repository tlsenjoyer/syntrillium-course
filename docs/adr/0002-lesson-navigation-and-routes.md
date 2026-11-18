# Give lessons browser-addressable routes

Represent each lesson as a distinct fragment URL in the offline player. Lesson
navigation adds browser history entries, so Back and Forward revisit lessons;
changing routes stops the old lesson's narration. Fragment routes preserve
direct offline use without a server or build step. The lesson list follows
course order, shows unavailable lessons as disabled, and previous/next lesson
controls stop at the course boundaries.

In the desktop app, lesson addresses are internal. Learners use the lesson
list to jump to a specific lesson and Previous Lesson or Next Lesson to move
in course order. For example, after jumping from lesson 2 to lesson 7,
Previous Lesson opens lesson 6.
