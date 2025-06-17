// // Main JavaScript for Photography Portfolio

// // Navigation smooth scrolling and active states
// document.addEventListener('DOMContentLoaded', function() {
//     // Smooth scrolling for navigation links
//     const navLinks = document.querySelectorAll('.nav-link');
//     navLinks.forEach(link => {
//         link.addEventListener('click', function(e) {
//             // Remove active class from all links
//             navLinks.forEach(l => l.classList.remove('active'));
//             // Add active class to clicked link
//             this.classList.add('active');
//         });
//     });

//     // Auto-hide flash messages after 5 seconds
//     const flashMessages = document.querySelectorAll('.flash-message');
//     flashMessages.forEach(message => {
//         setTimeout(() => {
//             message.style.opacity = '0';
//             setTimeout(() => {
//                 if (message.parentElement) {
//                     message.parentElement.removeChild(message);
//                 }
//             }, 300);
//         }, 5000);
//     });

//     // Initialize gallery if on home page
//     if (document.getElementById('galleryGrid')) {
//         initializeGallery();
//     }

//     // Initialize contact form validation
//     if (document.querySelector('.contact-form')) {
//         initializeContactForm();
//     }
// });

// // Gallery functionality
// function initializeGallery() {
//     const galleryItems = document.querySelectorAll('.gallery-item');
    
//     // Add intersection observer for lazy loading and animations
//     const observer = new IntersectionObserver((entries) => {
//         entries.forEach(entry => {
//             if (entry.isIntersecting) {
//                 entry.target.style.opacity = '1';
//                 entry.target.style.transform = 'translateY(0)';
//             }
//         });
//     }, {
//         threshold: 0.1,
//         rootMargin: '0px 0px -50px 0px'
//     });

//     galleryItems.forEach((item, index) => {
//         item.style.opacity = '0';
//         item.style.transform = 'translateY(30px)';
//         item.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
//         observer.observe(item);
//     });
// }

// // Album modal functionality
// function openAlbum(albumName, imageTitle) {
//     const modal = document.getElementById('albumModal');
//     const albumTitle = document.getElementById('albumTitle');
//     const albumGrid = document.getElementById('albumGrid');
    
//     if (!modal || !albumTitle || !albumGrid) return;
    
//     albumTitle.textContent = albumName;
//     albumGrid.innerHTML = '<div style="color: white; text-align: center; padding: 2rem;"><i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i><br>Loading album...</div>';
    
//     // Fetch album images
//     fetch(`/api/album/${encodeURIComponent(albumName)}`)
//         .then(response => {
//             if (!response.ok) {
//                 throw new Error('Network response was not ok');
//             }
//             return response.json();
//         })
//         .then(images => {
//             albumGrid.innerHTML = '';
            
//             if (images.length === 0) {
//                 albumGrid.innerHTML = '<div style="color: white; text-align: center; padding: 2rem;">No images found in this album.</div>';
//                 return;
//             }
            
//             images.forEach((image, index) => {
//                 const imgContainer = document.createElement('div');
//                 imgContainer.style.position = 'relative';
//                 imgContainer.style.overflow = 'hidden';
//                 imgContainer.style.borderRadius = '8px';
//                 imgContainer.style.cursor = 'pointer';
//                 imgContainer.style.opacity = '0';
//                 imgContainer.style.transform = 'scale(0.9)';
//                 imgContainer.style.transition = `opacity 0.3s ease ${index * 0.1}s, transform 0.3s ease ${index * 0.1}s`;
                
//                 const imgElement = document.createElement('img');
//                 imgElement.src = image.Image_URL;
//                 imgElement.alt = image.Title || 'Gallery Image';
//                 imgElement.loading = 'lazy';
//                 imgElement.style.width = '100%';
//                 imgElement.style.height = 'auto';
//                 imgElement.style.transition = 'transform 0.3s ease';
                
//                 imgElement.onload = () => {
//                     setTimeout(() => {
//                         imgContainer.style.opacity = '1';
//                         imgContainer.style.transform = 'scale(1)';
//                     }, index * 100);
//                 };
                
//                 imgContainer.addEventListener('mouseenter', () => {
//                     imgElement.style.transform = 'scale(1.05)';
//                 });
                
//                 imgContainer.addEventListener('mouseleave', () => {
//                     imgElement.style.transform = 'scale(1)';
//                 });
                
//                 imgContainer.onclick = () => openFullscreen(image.Image_URL, image.Title);
                
//                 imgContainer.appendChild(imgElement);
//                 albumGrid.appendChild(imgContainer);
//             });
//         })
//         .catch(error => {
//             console.error('Error loading album:', error);
//             albumGrid.innerHTML = '<div style="color: white; text-align: center; padding: 2rem;"><i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem; color: #ff6b6b;"></i><br>Error loading album images.<br><small>Please try again later.</small></div>';
//         });
    
//     modal.style.display = 'block';
//     document.body.style.overflow = 'hidden';
    
//     // Add fade-in animation
//     modal.style.opacity = '0';
//     setTimeout(() => {
//         modal.style.transition = 'opacity 0.3s ease';
//         modal.style.opacity = '1';
//     }, 10);
// }

// function closeModal() {
//     const modal = document.getElementById('albumModal');
//     if (!modal) return;
    
//     modal.style.opacity = '0';
//     setTimeout(() => {
//         modal.style.display = 'none';
//         document.body.style.overflow = 'auto';
//     }, 300);
// }

// function openFullscreen(imageUrl, title = '') {
//     const fullscreenDiv = document.createElement('div');
//     fullscreenDiv.className = 'fullscreen-viewer';
//     fullscreenDiv.style.cssText = `
//         position: fixed;
//         top: 0;
//         left: 0;
//         width: 100%;
//         height: 100%;
//         background-color: rgba(0, 0, 0, 0.95);
//         z-index: 3000;
//         display: flex;
//         align-items: center;
//         justify-content: center;
//         cursor: pointer;
//         opacity: 0;
//         transition: opacity 0.3s ease;
//     `;
    
//     const imgContainer = document.createElement('div');
//     imgContainer.style.cssText = `
//         position: relative;
//         max-width: 90%;
//         max-height: 90%;
//         display: flex;
//         flex-direction: column;
//         align-items: center;
//     `;
    
//     const img = document.createElement('img');
//     img.src = imageUrl;
//     img.alt = title;
//     img.style.cssText = `
//         max-width: 100%;
//         max-height: 90%;
//         object-fit: contain;
//         border-radius: 8px;
//         box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
//     `;
    
//     imgContainer.appendChild(img);
    
//     if (title) {
//         const titleElement = document.createElement('h3');
//         titleElement.textContent = title;
//         titleElement.style.cssText = `
//             color: white;
//             margin-top: 1rem;
//             text-align: center;
//             font-size: 1.2rem;
//             font-weight: 300;
//         `;
//         imgContainer.appendChild(titleElement);
//     }
    
//     // Close button
//     const closeBtn = document.createElement('button');
//     closeBtn.innerHTML = '&times;';
//     closeBtn.style.cssText = `
//         position: absolute;
//         top: 20px;
//         right: 20px;
//         background: rgba(255, 255, 255, 0.2);
//         border: none;
//         color: white;
//         font-size: 2rem;
//         width: 50px;
//         height: 50px;
//         border-radius: 50%;
//         cursor: pointer;
//         display: flex;
//         align-items: center;
//         justify-content: center;
//         transition: background 0.3s ease;
//     `;
    
//     closeBtn.addEventListener('mouseenter', () => {
//         closeBtn.style.background = 'rgba(255, 255, 255, 0.3)';
//     });
    
//     closeBtn.addEventListener('mouseleave', () => {
//         closeBtn.style.background = 'rgba(255, 255, 255, 0.2)';
//     });
    
//     const closeFullscreen = () => {
//         fullscreenDiv.style.opacity = '0';
//         setTimeout(() => {
//             if (document.body.contains(fullscreenDiv)) {
//                 document.body.removeChild(fullscreenDiv);
//             }
//             document.body.style.overflow = 'auto';
//         }, 300);
//     };
    
//     closeBtn.onclick = (e) => {
//         e.stopPropagation();
//         closeFullscreen();
//     };
    
//     fullscreenDiv.onclick = closeFullscreen;
//     imgContainer.onclick = (e) => e.stopPropagation();
    
//     fullscreenDiv.appendChild(imgContainer);
//     fullscreenDiv.appendChild(closeBtn);
//     document.body.appendChild(fullscreenDiv);
//     document.body.style.overflow = 'hidden';
    
//     // Fade in
//     setTimeout(() => {
//         fullscreenDiv.style.opacity = '1';
//     }, 10);
// }

// // Contact form functionality
// function initializeContactForm() {
//     const form = document.querySelector('.contact-form');
//     const submitBtn = form.querySelector('.btn-submit');
//     const originalBtnText = submitBtn.innerHTML;
    
//     // Add real-time validation
//     const inputs = form.querySelectorAll('input[required], textarea[required]');
//     inputs.forEach(input => {
//         input.addEventListener('blur', validateField);
//         input.addEventListener('input', clearError);
//     });
    
//     // Form submission handling
//     form.addEventListener('submit', function(e) {
//         e.preventDefault();
        
//         // Validate all required fields
//         let isValid = true;
//         inputs.forEach(input => {
//             if (!validateField.call(input)) {
//                 isValid = false;
//             }
//         });
        
//         if (!isValid) return;
        
//         // Show loading state
//         submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin" style="margin-right: 0.5rem;"></i>Sending...';
//         submitBtn.disabled = true;
        
//         // Submit form (this will be handled by Flask)
//         const formData = new FormData(form);
        
//         fetch(form.action || '/connect', {
//             method: 'POST',
//             body: formData
//         })
//         .then(response => {
//             if (response.ok) {
//                 return response.text();
//             }
//             throw new Error('Network response was not ok');
//         })
//         .then(() => {
//             // Show success state
//             submitBtn.innerHTML = '<i class="fas fa-check" style="margin-right: 0.5rem;"></i>Message Sent!';
//             submitBtn.style.background = '#28a745';
            
//             // Reset form after delay
//             setTimeout(() => {
//                 form.reset();
//                 submitBtn.innerHTML = originalBtnText;
//                 submitBtn.style.background = '';
//                 submitBtn.disabled = false;
//             }, 2000);
//         })
//         .catch(error => {
//             console.error('Error:', error);
//             submitBtn.innerHTML = '<i class="fas fa-exclamation-triangle" style="margin-right: 0.5rem;"></i>Error - Try Again';
//             submitBtn.style.background = '#dc3545';
            
//             setTimeout(() => {
//                 submitBtn.innerHTML = originalBtnText;
//                 submitBtn.style.background = '';
//                 submitBtn.disabled = false;
//             }, 3000);
//         });
//     });
// }

// function validateField() {
//     const field = this;
//     const value = field.value.trim();
    
//     // Remove existing error styles
//     field.style.borderColor = '';
//     const existingError = field.parentNode.querySelector('.field-error');
//     if (existingError) {
//         existingError.remove();
//     }
    
//     // Validate based on field type
//     let isValid = true;
//     let errorMessage = '';
    
//     if (field.hasAttribute('required') && !value) {
//         isValid = false;
//         errorMessage = 'This field is required';
//     } else if (field.type === 'email' && value) {
//         const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
//         if (!emailRegex.test(value)) {
//             isValid = false;
//             errorMessage = 'Please enter a valid email address';
//         }
//     }
    
//     if (!isValid) {
//         field.style.borderColor = '#dc3545';
//         const errorDiv = document.createElement('div');
//         errorDiv.className = 'field-error';
//         errorDiv.style.cssText = 'color: #dc3545; font-size: 0.8rem; margin-top: 0.25rem;';
//         errorDiv.textContent = errorMessage;
//         field.parentNode.appendChild(errorDiv);
//     }
    
//     return isValid;
// }

// function clearError() {
//     this.style.borderColor = '';
//     const existingError = this.parentNode.querySelector('.field-error');
//     if (existingError) {
//         existingError.remove();
//     }
// }

// // Global event listeners
// document.addEventListener('keydown', function(event) {
//     if (event.key === 'Escape') {
//         closeModal();
//         // Close fullscreen viewer
//         const fullscreenViewer = document.querySelector('.fullscreen-viewer');
//         if (fullscreenViewer) {
//             fullscreenViewer.click();
//         }
//     }
// });

// // Close modal when clicking outside
// window.addEventListener('click', function(event) {
//     const modal = document.getElementById('albumModal');
//     if (event.target === modal) {
//         closeModal();
//     }
// });

// // Smooth scroll behavior for internal links
// document.addEventListener('click', function(e) {
//     const link = e.target.closest('a[href^="#"]');
//     if (link) {
//         e.preventDefault();
//         const targetId = link.getAttribute('href').substring(1);
//         const targetElement = document.getElementById(targetId);
//         if (targetElement) {
//             targetElement.scrollIntoView({
//                 behavior: 'smooth',
//                 block: 'start'
//             });
//         }
//     }
// });

// // Performance optimization: Preload critical images
// function preloadCriticalImages() {
//     const galleryItems = document.querySelectorAll('.gallery-item img');
//     const criticalImages = Array.from(galleryItems).slice(0, 6); // Preload first 6 images
    
//     criticalImages.forEach(img => {
//         if (img.loading !== 'eager') {
//             const preloadImg = new Image();
//             preloadImg.src = img.src;
//         }
//     });
// }

// // Initialize preloading when page loads
// window.addEventListener('load', preloadCriticalImages);
