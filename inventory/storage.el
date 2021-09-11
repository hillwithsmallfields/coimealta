;;; storage.el --- inventory and storage lookup      -*- lexical-binding: t; -*-

;; Copyright (C) 2019  John Sturdy

;; Author: John Sturdy <jcg.sturdy@gmail.com>
;; Keywords: data

;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation, either version 3 of the License, or
;; (at your option) any later version.

;; This program is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with this program.  If not, see <https://www.gnu.org/licenses/>.

;;; Commentary:

;; Completion support and lookup for my inventory and storage csv files.

;;; Code:

(defvar storage-inventory-filename (substitute-in-file-name "$ORG/inventory.csv")
  "Where the inventory is stored.")

(defvar storage-inventory-table nil
  "Hash table from item names to number/location pairs.")

(defvar storage-books-filename (substitute-in-file-name "$ORG/books.csv")
  "Where the books are stored.")

(defvar storage-project-parts-filename (substitute-in-file-name "$ORG/project-parts.csv")
  "Where the project parts are stored.")

(defvar storage-stock-filename (substitute-in-file-name "$ORG/stock.csv")
  "Where the stock items stored.")

(defvar storage-locations-filename (substitute-in-file-name "$ORG/storage.csv")
  "Where the storage locations are stored.")

(defvar storage-locations-table nil
  "Hash table from storage location names to containing locations")

(defvar storage-locations-index-table nil
  "Hash table from storage location numbers to description/containing-location pairs.")

(defun safe-string-to-number (raw)
  "Convert RAW to a number."
  (cond
   ((stringp raw)
    (string-to-number raw))
   ((numberp raw)
    raw)
   ;; ((null raw) ; not needed, as handled by the default case
   ;;  0)
   (t
    0)))

(defvar field-names nil
  "The field names for this buffer.
Local to each buffer.")

(make-variable-buffer-local 'field-names)

(defun storage-get-column-names ()
  "Get the column names of this file."
  (interactive)
  (save-excursion
    (goto-char (point-min))
    (setq field-names (split-string
                       (buffer-substring-no-properties
                        (point) (line-end-position))
                       ",")))
  field-names)

(defun storage-read-csv (filename table
                                  name-field-name location-field-name
                                  &optional index-table index-field-name)
  "Read storage data from FILENAME into TABLE.
NAME-FIELD-NAME and LOCATION-FIELD-NAME are used to find the columns to use.
With optional INDEX-TABLE and INDEX-FIELD-NAME also store the name-location
pair into that table using that column."
  (find-file filename)
  (save-excursion
    (goto-char (point-min))
    (let* ((column-names (storage-get-column-names))
           (name-field-number (position name-field-name column-names :test 'string=))
           (index-field-number (if index-field-name
                                   (position index-field-name column-names :test 'string=)
                                 nil))
           (location-field-number (position location-field-name column-names :test 'string=)))
      (forward-line)
      (while (not (eobp))
        (let* ((cells (split-string
                       (buffer-substring-no-properties
                        (point) (line-end-position))
                       ","))
               (description (nth name-field-number cells))
               (location (safe-string-to-number (nth location-field-number cells))))
          (puthash description location table)
          (when index-table
            (puthash (safe-string-to-number (nth index-field-number cells))
                     (cons description location)
                     index-table)))
        (forward-line)))))

(defun storage-read-tables ()
  "Read the storage tables."
  (interactive)
  (save-window-excursion
    (save-excursion
      (setq storage-inventory-table (make-hash-table :test 'equal))
      (storage-read-csv storage-inventory-filename
                        storage-inventory-table
                        "Item" "Normal location")
      (storage-read-csv storage-books-filename
                        storage-inventory-table
                        "Title" "Location")
      (storage-read-csv storage-project-parts-filename
                        storage-inventory-table
                        "Item" "Normal location")
      (storage-read-csv storage-stock-filename
                        storage-inventory-table
                        "Item" "Normal location")
      (setq storage-locations-table (make-hash-table :test 'equal))
      (setq storage-locations-index-table (make-hash-table))
      (storage-read-csv storage-locations-filename
                        storage-locations-table
                        "Description" "ContainedWithin"
                        storage-locations-index-table "Number"))))

(defun storage-completing-read-item (prompt)
  "Read an item name, using PROMPT."
  (unless storage-inventory-table
    (storage-read-tables))
  (let ((completion-ignore-case t))
    (completing-read prompt storage-inventory-table nil t)))

(defun storage-completing-read-location (prompt)
  "Read a location name, using PROMPT."
  (unless storage-inventory-table
    (storage-read-tables))
  (let ((completion-ignore-case t))
    (completing-read prompt storage-locations-table nil t)))

(defun storage-nested-location (location)
  "Construct the surroundings of LOCATION.
LOCATION may be a description or a number."
  (when (stringp location)
    (setq location (gethash location storage-locations-table)))
  (let ((nest nil))
    (while (and location (not (zerop location)))
      (let ((loc-descr (gethash location storage-locations-index-table)))
        (push (car loc-descr) nest)
        (setq location (cdr loc-descr))))
    (nreverse nest)))

(defun storage-locate-item (item)
  "Locate ITEM."
  (interactive (progn (unless storage-inventory-table
                        (storage-read-tables))
                      (list (storage-completing-read-item "Locate item: "))))
  (unless storage-inventory-table
    (storage-read-tables))
  (let ((item-location (gethash item storage-inventory-table)))
    (if item-location
        (message "%s is in %s"
                 item
                 (mapconcat 'identity
                            (storage-nested-location item-location)
                            ", in "))
      (message "Could not locate %s" item))))

(defun set-cell (row key value)
  "Set the value of a cell in ROW, for column KEY, to VALUE.
The buffer-local variable `field-names' is used."
  (aset row (position key field-names :test 'equal) value))

(defun storage-add-item (item category price supplier)
  "Add an ITEM to the inventory, in CATEGORY at PRICE from SUPPLIER."
  (save-window-excursion
    (save-excursion
      (find-file storage-inventory-filename)
      (storage-get-column-names)
      (let* ((label-number (read-from-minibuffer "Label number: "))
             (storage-location (storage-completing-read-location (format "Storage location for %s: " item))))
        (goto-char (point-max))
        (let ((cells (make-vector (length field-names) "")))
          (set-cell cells "Label number" label-number)
          (set-cell cells "Item" item)
          (set-cell cells "Type" category)
          (set-cell cells "Origin" supplier)
          (set-cell cells "Normal location" storage-location)
          (set-cell cells "Approx value when bought" price)
          (insert (mapconcat 'identity cells ",")
                  "\n"))))))

(defun storage-add-part (item category price)
  "Add an ITEM to parts storage, in CATEGORY at PRICE."
  (save-window-excursion
    (save-excursion
      (find-file storage-project-parts-filename)
      (storage-get-column-names)
      (let* ((item-number (read-from-minibuffer "Item number: "))
             (storage-location (storage-completing-read-location (format "Storage location for %s: " item))))
        (goto-char (point-max))
        (let ((cells (make-vector (length field-names) "")))
          (set-cell cells "Item number" item-number)
          (set-cell cells "Item" item)
          (set-cell cells "Type" category)
          (set-cell cells "Normal location" storage-location)
          (insert (mapconcat 'identity cells ",")
                  "\n"))))))

(provide 'storage)
;;; storage.el ends here
