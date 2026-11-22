# Target maps

Edit target occupancy in `target_masks.jsx`; the builder loads that file with `$.evalFile`, so EffectCraft can use the data without enabling external file access.

- Each target is a named array of exactly 27 rows, each 27 characters wide.
- `#` means the cell forms part of the object; `.` leaves it in the background field.
- Row 1 is the top row and column 1 is the leftmost column.
- Select the target in `build.jsx` by setting `targetMask` to its name, such as `flame` or `heart`.
- Add another named map to `target_masks.jsx` to form a new silhouette. Keep the existing grid geometry, colors, and animation settings in `build.jsx`.

The included flame has 176 active cells; the heart has 274. This recipe reveals one selected shape from an empty grid. Turning one completed shape into another needs a separate cell-state transition; it is not vector-path morphing.
