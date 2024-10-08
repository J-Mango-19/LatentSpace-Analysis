import torch
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

def get_x_y_num_batches(dataloader, device, num_batches):
  """
  gets a specified number of batches from the dataloader and concatenates them into a single tensor
  """
  x, y = next(iter(dataloader))
  x, y = x.to(device), y.to(device)
  for batch in range(num_batches -1):
    x_2, y_2 = next(iter(dataloader))
    x_2, y_2 = x_2.to(device), y_2.to(device)
    x = torch.cat((x, x_2), dim=0)
    y = torch.cat((y, y_2), dim=0)
  return x, y

def get_x_by_label(label, batch_x, y):
  """
  takes a batch as input and returns one data example with the specified label
  """
  for i in range(y.shape[0]):
    if y[i].item() == label:
      return batch_x[i]

  print(f"Error: Could Not find an example of label {label} in this batch")

def get_average_z(class_label, y, x, model):
  """
  inferences the model on the data examples (x) filtered by the specified class (class_label) and returns the average latent vector generated for that class
  """
  x_by_class = x[y == class_label]
  avg_z_by_class = torch.mean(model(x_by_class)[0], dim=0)
  return avg_z_by_class

def compare_latent_spaces_exact(model_vae, model_ae, dataloader, random_z, num_batches=5):
    """
    Plots high-dimensionsal latent representations two dimensions at a time by sampling z from models as they perform inference
    Expects a VAE model, an AE model, and a random z vector as input. Plots corresponding dimensions from each model side-by-side for comparison
    Random z vector is shown in a distinct color in the same plots as the real examples.
    """

    if model_vae.latent_dim % 2 != 0:
      print("This function only plots even latent dims, try with even latent dim")
      return

    if model_vae.latent_dim != model_ae.latent_dim:
      print("this function only compares latent dims for models with equal latent dims. Ensure latent dims are = for both models.")
      return

    latent_figs, latent_axes = plt.subplots(int(model_vae.latent_dim / 2), 2, figsize=(6, 3 * (int(model_vae.latent_dim / 2 ))))

    device = next(model_vae.parameters()).device.type
    x, y = get_x_y_num_batches(dataloader, device, num_batches)

    z_vae, _, _, _, = model_vae(x)
    z_ae, _ = model_ae(x)

    # plot the actual latent dimensions and show where the randomly sampled vector is located, for each model
    for vertical_pos in range(int(model_vae.latent_dim / 2)):
      latent_axes[vertical_pos][0].axhline(0, color='black', linewidth=1)
      latent_axes[vertical_pos][0].axvline(0, color='black', linewidth=1)
      latent_axes[vertical_pos][1].axhline(0, color='black', linewidth=1)
      latent_axes[vertical_pos][1].axvline(0, color='black', linewidth=1)
      latent_axes[vertical_pos][0].set_xlim(-10, 10)
      latent_axes[vertical_pos][0].set_ylim(-10, 10)
      latent_axes[vertical_pos][1].set_xlim(-10, 10)
      latent_axes[vertical_pos][1].set_ylim(-10, 10)
      latent_axes[vertical_pos][0].set_aspect('equal', 'box')
      latent_axes[vertical_pos][1].set_aspect('equal', 'box')
      latent_axes[vertical_pos][0].set_xlabel(f'Z_{vertical_pos}')
      latent_axes[vertical_pos][1].set_ylabel(f'Z_{vertical_pos + 1}')

      # every column of z_vae and z_ae is a dimension in latent space. Plot 2 dims at a time.
      # use all rows becuase this plots all encoded examples at once, in every plot
      latent_axes[vertical_pos][0].scatter(x = z_vae[:, vertical_pos * 2].cpu().detach(), y = z_vae[:, vertical_pos * 2 + 1].cpu().detach(), label='Latents from real examples', color='blue')
      latent_axes[vertical_pos][1].scatter(x = z_ae[:, vertical_pos * 2].cpu().detach(), y = z_ae[:, vertical_pos * 2 + 1].cpu().detach(), label='Latents rom real examples', color='blue')

      # titles
      latent_axes[vertical_pos][0].set_title(f'VAE latent space: Z_{vertical_pos * 2} and Z_{vertical_pos * 2 + 1}')
      latent_axes[vertical_pos][1].set_title(f'AE latent space: Z_{vertical_pos * 2} and Z_{vertical_pos * 2 + 1}')

      # plot the input vector for comparison
      latent_axes[vertical_pos][0].scatter(x = random_z[vertical_pos * 2].cpu(), y=random_z[vertical_pos * 2 +1].cpu(), label='Randomly generated latent', color='red')
      latent_axes[vertical_pos][1].scatter(x = random_z[vertical_pos * 2].cpu(), y=random_z[vertical_pos * 2 +1].cpu(), label='Randomly generated latent', color='red')

      latent_axes[vertical_pos][0].legend(loc="upper right")
      latent_axes[vertical_pos][1].legend(loc="upper right")

    plt.tight_layout()
    plt.show()

def plot_latent_space_summary(model_vae, model_ae, dataloader, num_batches=15):
  """
  Plots the latent vectors generated by two models side-by-side and colors latent vectors by class to visualize class groupings.
  Calls a function that plots latent vectors directly if they are less than 3-dimensional, otherwise calls a function to plot their TSNE representations
  """

  colors_list = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'orange', 'purple', 'brown']

  if model_vae.latent_dim != model_ae.latent_dim:
    print("Latent dimension mismatch.")
    return
  if model_vae.latent_dim < 3:
    # plot 2d
    plot_latent_2d(model_vae, model_ae, dataloader, colors_list, num_batches)
  else:
    # plot tsne
    plot_latent_TSNE(model_vae, model_ae, dataloader, colors_list, num_batches)

def plot_latent_TSNE(model_vae, model_ae, dataloader, colors_list, num_batches=15):
  """
  Called by plot_latent_space_summary when the models' latent space dimension > 2
  Takes two models as input, which perform inference on data examples from dataloader,with each model generating a latent vector for each data example
  The TSNE representations of the models' corresponding latent vectors are visualized in two side-by-side plots
  """

  plt.rcParams['figure.figsize'] = [12.5, 5]
  tsne_figs, tsne_axs = plt.subplots(1, 2)

  tsne_vae = TSNE(n_components=2)
  tsne_ae = TSNE(n_components=2)

  device = next(model_vae.parameters()).device.type
  x, y = get_x_y_num_batches(dataloader, device, num_batches)

  encoded_vae, _, _, _ = model_vae(x)
  encoded_ae, _ = model_ae(x)

  classes_as_colors = [colors_list[y_cur] for y_cur in y]

  z_vae_embedded = tsne_vae.fit_transform(encoded_vae.cpu().detach())
  z_ae_embedded = tsne_ae.fit_transform(encoded_ae.cpu().detach())

  tsne_axs[0].set_title('VAE Latent Space - TSNE representation')
  tsne_axs[1].set_title('AE Latent Space - TSNE representation')
  for ax in tsne_axs:
      ax.set_xticks([])
      ax.set_yticks([])

  tsne_axs[0].scatter(z_vae_embedded[:, 0], z_vae_embedded[:, 1], c=classes_as_colors)
  tsne_axs[1].scatter(z_ae_embedded[:, 0], z_ae_embedded[:, 1], c=classes_as_colors)
  plt.show()

def plot_latent_2d(model_vae, model_ae, dataloader, colors_list, num_batches=15):
  """
  Called by plot_latent_space_summary when the models' latent space dimension < 3
  Takes two models as input, which perform inference on data examples from dataloader,with each model generating a latent vector for each data example
  The models' corresponding latent vectors are visualized in two side-by-side plots
  """
  plt.rcParams['figure.figsize'] = [12.5, 5]
  fig, axs = plt.subplots(1, 2)
  device = next(model_vae.parameters()).device.type
  x, y = get_x_y_num_batches(dataloader, device, num_batches)
  classes_as_colors = [colors_list[y_cur] for y_cur in y]

  z_vae, _, _, _ = model_vae(x)
  z_ae, _ = model_ae(x)

  axs[0].set_title('VAE Latent Space - real 2d points (only 2 latent dims found)')
  axs[1].set_title('AE Latent Space - real 2d points')

  axs[0].scatter(z_vae[:, 0].cpu().detach(), z_vae[:, 1].cpu().detach(), c=classes_as_colors)
  axs[1].scatter(z_ae[:, 0].cpu().detach(), z_ae[:, 1].cpu().detach(), c=classes_as_colors)
  plt.show()

def traverse_latent_space(start_z_vae, start_z_ae, model_vae, model_ae, dimension_to_change=0, rate_of_change=1):
  """
  Visualizes reconstructions of two latent vectors as the vectors are added to and subtracted from along the specified dimension(s) by rate_of_change
  """

  plt.rcParams['figure.figsize'] = [20, 5]
  num_samples = 11

  fig_interpolate_zero, axs_interpolate_zero = plt.subplots(2, num_samples)
  axs_interpolate_zero[0][5].set_title('original VAE reconstruction')
  axs_interpolate_zero[1][5].set_title('original AE reconstruction')
  axs_interpolate_zero[0][3].set_title(f'<-- subtracting {rate_of_change} from entry {dimension_to_change}')
  axs_interpolate_zero[1][3].set_title(f'<-- subtracting {rate_of_change} from entry {dimension_to_change}')
  axs_interpolate_zero[0][7].set_title(f'adding {rate_of_change} to entry {dimension_to_change}-->')
  axs_interpolate_zero[1][7].set_title(f'adding {rate_of_change} to entry {dimension_to_change}-->')
  for item in axs_interpolate_zero[:]:
    for plot in item:
      plot.set_xticks([])
      plot.set_yticks([])

  start_z_vae[dimension_to_change] -= rate_of_change * int(num_samples/2 + 1)
  start_z_ae[dimension_to_change] -= rate_of_change * int(num_samples/2 + 1)

  for sample in range(num_samples):
    start_z_vae[dimension_to_change] += rate_of_change
    start_z_ae[dimension_to_change] += rate_of_change

    vae_recon = model_vae.decoder(start_z_vae)
    ae_recon = model_ae.decoder(start_z_ae)

    axs_interpolate_zero[0][sample].imshow(vae_recon.cpu().detach().numpy().transpose(1, 2, 0))
    axs_interpolate_zero[1][sample].imshow(ae_recon.cpu().detach().numpy().transpose(1, 2, 0))

  plt.show()

def interpolate_btwn_classes(class_start, class_end, x, y, model_in, num_steps=5, alpha=1):
  """
  Calculates the difference beteeen a model's average latent vectors for two classes, then incrementally adds this difference to one class.
  The decoder's reconstruction of these incremental changes are visualized in several images
  """
  plt.rcParams['figure.figsize'] = [20, 5]
  start_avg_z = get_average_z(class_start, y, x, model_in)
  end_avg_z = get_average_z(class_end, y, x, model_in)

  # get a starting sample vector
  x_sample_start = get_x_by_label(class_start, x, y).unsqueeze(dim=0)
  try:
    z_sample_start, recon_start, _, _ = model_in(x_sample_start)
  except ValueError:
    z_sample_start, recon_start = model_in(x_sample_start)

  # interpolate btwn classes
  figc, axsc = plt.subplots(1, num_steps+1)
  axsc[0].set_title(f'Original img from class {class_start}')
  axsc[0].imshow(x_sample_start.cpu().squeeze(dim=0).detach().numpy().transpose(1, 2, 0))
  axsc[1].set_title('Reconstruction of original image')
  axsc[-1].set_title(f'Interpolated img from {class_start} to {class_end}')

  for ax in axsc:
      ax.set_xticks([])
      ax.set_yticks([])

  for step in range(num_steps):
    z_to_add = alpha * step * (1/(num_steps-1)) * (end_avg_z - start_avg_z)
    axsc[step+1].imshow(model_in.decoder(z_sample_start + z_to_add).cpu().detach().squeeze(dim=0).numpy().transpose(1, 2, 0))

  plt.show()

def show_random_samples(model_vae, model_ae, input_z, num_samples=4):
  """
  displays decoder reconstructions of two model's decoders' reconstructions of latent vectors sampled from a normal distributon and an input latent vector
  """
  device = next(model_vae.parameters()).device.type

  fig, axs = plt.subplots(num_samples, 2, figsize=(12, 3 * (num_samples)))

  vae_recon = model_vae.decoder(input_z)
  ae_recon = model_ae.decoder(input_z)

  # Show input latent vector reconstruction
  axs[0][0].imshow(vae_recon.cpu().detach().numpy().transpose(1, 2, 0))
  axs[0][0].set_title('VAE reconstruction of input latent')

  axs[0][1].imshow(ae_recon.cpu().detach().numpy().transpose(1, 2, 0))
  axs[0][1].set_title('AE reconstruction of input latent')

  for row in range(1, num_samples):
    random_z = torch.randn(model_vae.latent_dim).to(device)
    vae_recon = model_vae.decoder(random_z)
    ae_recon = model_ae.decoder(random_z)

    axs[row][0].set_title(f'VAE reconstruction of randomly generated latent #{row}')
    axs[row][0].set_xticks([])
    axs[row][0].set_yticks([])
    axs[row][0].imshow(vae_recon.cpu().detach().numpy().transpose(1, 2, 0))

    axs[row][1].set_title(f'AE reconstruction of randomly generated latent #{row}')
    axs[row][1].set_xticks([])
    axs[row][1].set_yticks([])
    axs[row][1].imshow(ae_recon.cpu().detach().numpy().transpose(1, 2, 0))

  fig.tight_layout()
  plt.show()

def display_reconstructed_x(dataloader, model_vae, model_ae, num_reconstructions=5):
  """
  plots a data example x alongside two models' reconstructions of the image
  """
  device = next(model_vae.parameters()).device.type
  x, _ = next(iter(dataloader))
  x = x.to(device)
  _, recon_vae, _, _ = model_vae(x)
  _, recon_ae = model_ae(x)

  fig, axs = plt.subplots(num_reconstructions, 3, figsize=(12, 3 * num_reconstructions))

  for row in range(num_reconstructions):
    # show original image
    axs[row][0].set_title('Original image')
    axs[row][0].set_xticks([])
    axs[row][0].set_yticks([])
    axs[row][0].imshow(x[row].cpu().numpy().transpose(1, 2, 0))

    # show VAE reconstruction
    axs[row][1].set_title('VAE reconstruction')
    axs[row][1].set_xticks([])
    axs[row][1].set_yticks([])
    axs[row][1].imshow(recon_vae[row].cpu().detach().numpy().transpose(1, 2, 0))

    # show AE reconstruction
    axs[row][2].set_title('AE reconstruction')
    axs[row][2].set_xticks([])
    axs[row][2].set_yticks([])
    axs[row][2].imshow(recon_ae[row].cpu().detach().numpy().transpose(1, 2, 0))


  fig.tight_layout()
  plt.show()
